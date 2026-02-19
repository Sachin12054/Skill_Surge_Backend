from fastapi import APIRouter, HTTPException, Depends
from app.models import KnowledgeGraphResponse, GraphNode, GraphEdge
from app.core import get_neo4j_service
from app.api.deps import get_current_user

router = APIRouter(prefix="/graph", tags=["Graph Navigator"])


@router.get("/{course_id}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    course_id: str,
    depth: int = 2,
    current_user: dict = Depends(get_current_user),
):
    """Get the knowledge graph for a course."""
    neo4j = get_neo4j_service()
    
    try:
        result = await neo4j.get_knowledge_graph(course_id, depth)
        
        nodes = [
            GraphNode(
                id=n["id"],
                label=n["label"],
                type=n.get("type", "concept"),
                size=n.get("size", 1.0),
                color=n.get("color"),
            )
            for n in result.get("nodes", [])
        ]
        
        edges = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                weight=e.get("weight", 1.0),
                label=e.get("label"),
            )
            for e in result.get("edges", [])
        ]
        
        return KnowledgeGraphResponse(nodes=nodes, edges=edges)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{course_id}/similar/{concept_id}")
async def find_similar_concepts(
    course_id: str,
    concept_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """Find concepts similar to a given concept."""
    neo4j = get_neo4j_service()
    
    # First, get the concept's embedding
    from app.core import get_supabase_service
    supabase = get_supabase_service()
    
    # Get embedding from Supabase (if stored there)
    # This is a simplified version - in production, store embeddings in Neo4j
    
    # For now, return connected concepts
    result = await neo4j.get_knowledge_graph(course_id)
    
    # Filter to concepts connected to the given one
    connected = set()
    for edge in result.get("edges", []):
        if edge["source"] == concept_id:
            connected.add(edge["target"])
        elif edge["target"] == concept_id:
            connected.add(edge["source"])
    
    similar = [
        n for n in result.get("nodes", [])
        if n["id"] in connected
    ][:limit]
    
    return {"similar_concepts": similar}


@router.get("/{course_id}/path")
async def find_concept_path(
    course_id: str,
    from_concept: str,
    to_concept: str,
    current_user: dict = Depends(get_current_user),
):
    """Find the learning path between two concepts."""
    neo4j = get_neo4j_service()
    
    try:
        path = await neo4j.get_concept_path(from_concept, to_concept)
        return {
            "path": path,
            "steps": len(path) - 1 if path else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{course_id}/index")
async def index_course_content(
    course_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Index course content into the knowledge graph."""
    from app.core import get_supabase_service, get_bedrock_service
    from app.services import get_pdf_processor
    import json
    import uuid
    
    supabase = get_supabase_service()
    bedrock = get_bedrock_service()
    pdf_processor = get_pdf_processor()
    neo4j = get_neo4j_service()
    
    # Get course materials
    materials = await supabase.select(
        "materials",
        "*",
        {"course_id": course_id}
    )
    
    all_concepts = []
    
    for material in materials.data:
        # Download and extract text (download_file is sync, no await)
        pdf_bytes = supabase.download_file(
            "course-materials",
            material["file_path"]
        )
        content = await pdf_processor.extract_text(pdf_bytes)
        
        # Extract concepts using AI
        prompt = f"""Extract key concepts from this academic content.

Content (truncated):
{content[:15000]}

Return a JSON array of concepts with:
- name: concept name
- description: brief description
- related_to: array of other concept names this relates to

Return ONLY the JSON array."""

        response = await bedrock.invoke_claude(prompt, max_tokens=2000)
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            concepts = json.loads(response)
            all_concepts.extend(concepts)
        except json.JSONDecodeError:
            continue
    
    # Create nodes in Neo4j
    created_nodes = {}
    for concept in all_concepts:
        concept_id = str(uuid.uuid4())
        try:
            await neo4j.create_concept_node(
                concept_id=concept_id,
                name=concept["name"],
                description=concept.get("description", ""),
                course_id=course_id,
            )
            created_nodes[concept["name"]] = concept_id
        except Exception:
            continue
    
    # Create relationships
    for concept in all_concepts:
        if concept["name"] in created_nodes:
            for related in concept.get("related_to", []):
                if related in created_nodes:
                    try:
                        await neo4j.create_relationship(
                            from_id=created_nodes[concept["name"]],
                            to_id=created_nodes[related],
                            relationship_type="RELATES_TO",
                        )
                    except Exception:
                        continue
    
    return {
        "indexed": True,
        "concepts_created": len(created_nodes),
    }
