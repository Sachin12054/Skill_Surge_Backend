from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core import get_supabase_service
from app.api.deps import get_current_user
import uuid

router = APIRouter(prefix="/space", tags=["Study Space"])


# Pydantic models
class SubjectCreate(BaseModel):
    name: str
    color: Optional[str] = "#6366F1"
    icon: Optional[str] = "folder"


class SubjectResponse(BaseModel):
    id: str
    name: str
    color: str
    icon: str
    pdf_count: int
    created_at: datetime


class PDFResponse(BaseModel):
    id: str
    name: str
    file_path: str
    file_size: int
    subject_id: Optional[str]
    subject_name: Optional[str]
    uploaded_at: datetime


class AssignPDFRequest(BaseModel):
    pdf_ids: List[str]
    subject_id: Optional[str]  # None to unassign


@router.get("/subjects")
async def get_subjects(user: dict = Depends(get_current_user)):
    """Get all subjects for the current user."""
    supabase = get_supabase_service()
    
    try:
        # Get subjects with PDF count
        result = supabase.admin_client.table("subjects").select(
            "*, pdfs:space_pdfs(count)"
        ).eq("user_id", user["id"]).order("name").execute()
        
        subjects = []
        for s in result.data or []:
            subjects.append({
                "id": s["id"],
                "name": s["name"],
                "color": s.get("color", "#6366F1"),
                "icon": s.get("icon", "folder"),
                "pdf_count": s.get("pdfs", [{}])[0].get("count", 0) if s.get("pdfs") else 0,
                "created_at": s["created_at"],
            })
        
        print(f"Found {len(subjects)} subjects for user {user['id']}")
        return {"subjects": subjects}
    except Exception as e:
        # Return empty if table doesn't exist yet
        print(f"Error fetching subjects: {e}")
        return {"subjects": []}


@router.post("/subjects")
async def create_subject(
    data: SubjectCreate,
    user: dict = Depends(get_current_user),
):
    """Create a new subject/folder."""
    supabase = get_supabase_service()
    
    subject_id = str(uuid.uuid4())
    
    result = supabase.admin_client.table("subjects").insert({
        "id": subject_id,
        "user_id": user["id"],
        "name": data.name,
        "color": data.color,
        "icon": data.icon,
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    
    return {
        "id": subject_id,
        "name": data.name,
        "color": data.color,
        "icon": data.icon,
        "pdf_count": 0,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a subject (PDFs are unassigned, not deleted)."""
    supabase = get_supabase_service()
    
    # Unassign PDFs first
    supabase.admin_client.table("space_pdfs").update({
        "subject_id": None
    }).eq("subject_id", subject_id).execute()
    
    # Delete subject
    supabase.admin_client.table("subjects").delete().eq(
        "id", subject_id
    ).eq("user_id", user["id"]).execute()
    
    return {"success": True}


@router.get("/pdfs")
async def get_pdfs(
    subject_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get all PDFs, optionally filtered by subject."""
    supabase = get_supabase_service()
    
    try:
        query = supabase.admin_client.table("space_pdfs").select(
            "*, subject:subjects(id, name, color)"
        ).eq("user_id", user["id"])
        
        if subject_id:
            if subject_id == "unassigned":
                query = query.is_("subject_id", "null")
            else:
                query = query.eq("subject_id", subject_id)
        
        result = query.order("name").execute()
        
        pdfs = []
        for p in result.data or []:
            pdfs.append({
                "id": p["id"],
                "name": p["name"],
                "file_path": p["file_path"],
                "file_size": p.get("file_size", 0),
                "subject_id": p.get("subject_id"),
                "subject_name": p.get("subject", {}).get("name") if p.get("subject") else None,
                "subject_color": p.get("subject", {}).get("color") if p.get("subject") else None,
                "uploaded_at": p["uploaded_at"],
            })
        
        print(f"Found {len(pdfs)} PDFs for user {user['id']}")
        return {"pdfs": pdfs}
    except Exception as e:
        print(f"Error fetching PDFs: {e}")
        return {"pdfs": []}


@router.post("/pdfs/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    subject_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """Upload a PDF to the user's space."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    supabase = get_supabase_service()
    
    # Read file
    content = await file.read()
    file_size = len(content)
    
    # Generate unique path
    pdf_id = str(uuid.uuid4())
    storage_path = f"{user['id']}/space/{pdf_id}.pdf"
    
    # Upload to Supabase Storage (course-materials bucket)
    supabase.upload_file("course-materials", storage_path, content, "application/pdf")
    
    # Save metadata to database
    supabase.admin_client.table("space_pdfs").insert({
        "id": pdf_id,
        "user_id": user["id"],
        "name": file.filename,
        "file_path": storage_path,
        "file_size": file_size,
        "subject_id": subject_id if subject_id else None,
        "uploaded_at": datetime.utcnow().isoformat(),
    }).execute()
    
    return {
        "id": pdf_id,
        "name": file.filename,
        "file_path": storage_path,
        "file_size": file_size,
        "subject_id": subject_id,
        "uploaded_at": datetime.utcnow().isoformat(),
    }


@router.post("/pdfs/assign")
async def assign_pdfs(
    data: AssignPDFRequest,
    user: dict = Depends(get_current_user),
):
    """Assign multiple PDFs to a subject."""
    supabase = get_supabase_service()
    
    for pdf_id in data.pdf_ids:
        supabase.admin_client.table("space_pdfs").update({
            "subject_id": data.subject_id
        }).eq("id", pdf_id).eq("user_id", user["id"]).execute()
    
    return {"success": True, "updated": len(data.pdf_ids)}


@router.delete("/pdfs/{pdf_id}")
async def delete_pdf(
    pdf_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a PDF from space."""
    supabase = get_supabase_service()
    
    # Get file path first
    result = supabase.admin_client.table("space_pdfs").select("file_path").eq(
        "id", pdf_id
    ).eq("user_id", user["id"]).execute()
    
    if result.data:
        # Delete from storage
        try:
            supabase.delete_file("course-materials", result.data[0]["file_path"])
        except:
            pass
        
        # Delete from database
        supabase.admin_client.table("space_pdfs").delete().eq(
            "id", pdf_id
        ).eq("user_id", user["id"]).execute()
    
    return {"success": True}


@router.get("/pdfs/{pdf_id}/content")
async def get_pdf_content(
    pdf_id: str,
    user: dict = Depends(get_current_user),
):
    """Get PDF file content (for use in other features)."""
    supabase = get_supabase_service()
    
    # Get file path
    result = supabase.admin_client.table("space_pdfs").select("*").eq(
        "id", pdf_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf = result.data[0]
    
    # Get file from storage
    content = supabase.download_file("course-materials", pdf["file_path"])
    
    return {
        "id": pdf_id,
        "name": pdf["name"],
        "content": content,  # bytes
    }


@router.put("/subjects/{subject_id}")
async def update_subject(
    subject_id: str,
    data: SubjectCreate,
    user: dict = Depends(get_current_user),
):
    """Update a subject."""
    supabase = get_supabase_service()
    
    supabase.admin_client.table("subjects").update({
        "name": data.name,
        "color": data.color,
        "icon": data.icon,
    }).eq("id", subject_id).eq("user_id", user["id"]).execute()
    
    return {"success": True}


@router.get("/pdfs/{pdf_id}/url")
async def get_pdf_url(
    pdf_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a signed URL for viewing a PDF."""
    supabase = get_supabase_service()
    
    # Get PDF metadata
    result = supabase.admin_client.table("space_pdfs").select("*").eq(
        "id", pdf_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf = result.data[0]
    
    # Create signed URL for viewing (valid for 1 hour)
    signed_url = supabase.admin_client.storage.from_("course-materials").create_signed_url(
        pdf["file_path"], 3600
    )
    
    return {
        "url": signed_url.get("signedURL") or signed_url.get("signedUrl"),
        "name": pdf["name"],
    }
