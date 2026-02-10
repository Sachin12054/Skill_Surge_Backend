from neo4j import GraphDatabase
from functools import lru_cache
from typing import List, Dict, Any, Optional
from app.core.config import get_settings

settings = get_settings()


@lru_cache()
def get_neo4j_driver():
    """Get cached Neo4j driver."""
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


class Neo4jService:
    """Service class for Neo4j graph database operations."""
    
    def __init__(self):
        self.driver = get_neo4j_driver()
    
    def close(self):
        """Close the driver connection."""
        self.driver.close()
    
    async def create_concept_node(
        self,
        concept_id: str,
        name: str,
        description: str,
        course_id: str,
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Create a concept node in the graph."""
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (c:Concept {
                    id: $id,
                    name: $name,
                    description: $description,
                    courseId: $course_id,
                    embedding: $embedding,
                    createdAt: datetime()
                })
                RETURN c
                """,
                id=concept_id,
                name=name,
                description=description,
                course_id=course_id,
                embedding=embedding,
            )
            return result.single()["c"]
    
    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        weight: float = 1.0,
        properties: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create a relationship between two concepts."""
        props = properties or {}
        props["weight"] = weight
        
        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH (a:Concept {{id: $from_id}})
                MATCH (b:Concept {{id: $to_id}})
                CREATE (a)-[r:{relationship_type} $props]->(b)
                RETURN r
                """,
                from_id=from_id,
                to_id=to_id,
                props=props,
            )
            return result.single()["r"]
    
    async def get_knowledge_graph(
        self,
        course_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Get the knowledge graph for a course."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Concept {courseId: $course_id})
                OPTIONAL MATCH (c)-[r]-(related:Concept {courseId: $course_id})
                RETURN c, collect(distinct r) as relationships, collect(distinct related) as related_concepts
                """,
                course_id=course_id,
            )
            
            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()
            
            for record in result:
                concept = record["c"]
                if concept["id"] not in seen_nodes:
                    nodes.append({
                        "id": concept["id"],
                        "label": concept["name"],
                        "type": "concept",
                        "size": 1,
                    })
                    seen_nodes.add(concept["id"])
                
                for rel in record["relationships"]:
                    if rel:
                        edge_key = f"{rel.start_node['id']}-{rel.end_node['id']}"
                        if edge_key not in seen_edges:
                            edges.append({
                                "source": rel.start_node["id"],
                                "target": rel.end_node["id"],
                                "weight": rel.get("weight", 1.0),
                            })
                            seen_edges.add(edge_key)
                
                for related in record["related_concepts"]:
                    if related and related["id"] not in seen_nodes:
                        nodes.append({
                            "id": related["id"],
                            "label": related["name"],
                            "type": "concept",
                            "size": 1,
                        })
                        seen_nodes.add(related["id"])
            
            return {"nodes": nodes, "edges": edges}
    
    async def find_similar_concepts(
        self,
        embedding: List[float],
        course_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find similar concepts using vector similarity."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Concept {courseId: $course_id})
                WHERE c.embedding IS NOT NULL
                WITH c, gds.similarity.cosine(c.embedding, $embedding) AS similarity
                ORDER BY similarity DESC
                LIMIT $limit
                RETURN c, similarity
                """,
                course_id=course_id,
                embedding=embedding,
                limit=limit,
            )
            
            return [
                {
                    "concept": dict(record["c"]),
                    "similarity": record["similarity"],
                }
                for record in result
            ]
    
    async def get_concept_path(
        self,
        from_id: str,
        to_id: str,
    ) -> List[Dict[str, Any]]:
        """Find the shortest path between two concepts."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = shortestPath(
                    (a:Concept {id: $from_id})-[*]-(b:Concept {id: $to_id})
                )
                RETURN path
                """,
                from_id=from_id,
                to_id=to_id,
            )
            
            record = result.single()
            if not record:
                return []
            
            path = record["path"]
            return [dict(node) for node in path.nodes]


def get_neo4j_service() -> Neo4jService:
    """Get Neo4j service instance."""
    return Neo4jService()
