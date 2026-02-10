from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, date
from app.core import get_supabase_service
from app.api.deps import get_current_user
import uuid

router = APIRouter(prefix="/timer", tags=["Study Timer"])


# ============ Pydantic Models ============

class TimerSettings(BaseModel):
    focus_duration: int = 25
    short_break_duration: int = 5
    long_break_duration: int = 15
    sessions_until_long_break: int = 4
    auto_start_breaks: bool = True
    auto_start_focus: bool = False
    sound_enabled: bool = True
    vibration_enabled: bool = True
    notification_enabled: bool = True
    daily_goal_minutes: int = 120
    weekly_goal_minutes: int = 600


class StartSessionRequest(BaseModel):
    session_type: str = "focus"  # focus, short_break, long_break
    duration_minutes: int = 25
    subject_id: Optional[str] = None
    deck_id: Optional[str] = None
    activity_type: Optional[str] = None  # flashcards, quiz, reading, notes, general


class EndSessionRequest(BaseModel):
    session_id: str
    actual_duration_seconds: int
    completed: bool = True
    focus_rating: Optional[int] = None
    notes: Optional[str] = None
    distractions_count: int = 0


class PauseSessionRequest(BaseModel):
    session_id: str


class ResumeSessionRequest(BaseModel):
    session_id: str
    pause_duration_seconds: int


# ============ Settings Endpoints ============

@router.get("/settings")
async def get_timer_settings(user: dict = Depends(get_current_user)):
    """Get user's timer settings."""
    supabase = get_supabase_service()
    
    result = supabase.admin_client.table("timer_settings").select("*").eq(
        "user_id", user["id"]
    ).execute()
    
    if result.data:
        settings = result.data[0]
        return {
            "focus_duration": settings.get("focus_duration", 25),
            "short_break_duration": settings.get("short_break_duration", 5),
            "long_break_duration": settings.get("long_break_duration", 15),
            "sessions_until_long_break": settings.get("sessions_until_long_break", 4),
            "auto_start_breaks": settings.get("auto_start_breaks", True),
            "auto_start_focus": settings.get("auto_start_focus", False),
            "sound_enabled": settings.get("sound_enabled", True),
            "vibration_enabled": settings.get("vibration_enabled", True),
            "notification_enabled": settings.get("notification_enabled", True),
            "daily_goal_minutes": settings.get("daily_goal_minutes", 120),
            "weekly_goal_minutes": settings.get("weekly_goal_minutes", 600),
        }
    
    # Return defaults if no settings exist
    return TimerSettings().model_dump()


@router.put("/settings")
async def update_timer_settings(
    settings: TimerSettings,
    user: dict = Depends(get_current_user)
):
    """Update user's timer settings."""
    supabase = get_supabase_service()
    
    # Check if settings exist
    existing = supabase.admin_client.table("timer_settings").select("id").eq(
        "user_id", user["id"]
    ).execute()
    
    settings_data = {
        "user_id": user["id"],
        **settings.model_dump(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    if existing.data:
        # Update existing
        supabase.admin_client.table("timer_settings").update(
            settings_data
        ).eq("user_id", user["id"]).execute()
    else:
        # Create new
        settings_data["id"] = str(uuid.uuid4())
        settings_data["created_at"] = datetime.utcnow().isoformat()
        supabase.admin_client.table("timer_settings").insert(settings_data).execute()
    
    return {"success": True, "settings": settings.model_dump()}


# ============ Session Endpoints ============

@router.post("/session/start")
async def start_study_session(
    data: StartSessionRequest,
    user: dict = Depends(get_current_user)
):
    """Start a new study/break session."""
    supabase = get_supabase_service()
    
    # Check for any active sessions and end them
    active = supabase.admin_client.table("study_sessions").select("id").eq(
        "user_id", user["id"]
    ).eq("status", "active").execute()
    
    if active.data:
        # Mark active session as cancelled
        for session in active.data:
            supabase.admin_client.table("study_sessions").update({
                "status": "cancelled",
                "ended_at": datetime.utcnow().isoformat(),
            }).eq("id", session["id"]).execute()
    
    session_id = str(uuid.uuid4())
    session_data = {
        "id": session_id,
        "user_id": user["id"],
        "session_type": data.session_type,
        "duration_minutes": data.duration_minutes,
        "subject_id": data.subject_id,
        "deck_id": data.deck_id,
        "activity_type": data.activity_type,
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
    }
    
    supabase.admin_client.table("study_sessions").insert(session_data).execute()
    
    return {
        "session_id": session_id,
        "session_type": data.session_type,
        "duration_minutes": data.duration_minutes,
        "started_at": session_data["started_at"],
    }


@router.post("/session/pause")
async def pause_study_session(
    data: PauseSessionRequest,
    user: dict = Depends(get_current_user)
):
    """Pause an active session."""
    supabase = get_supabase_service()
    
    result = supabase.admin_client.table("study_sessions").update({
        "status": "paused",
        "paused_at": datetime.utcnow().isoformat(),
    }).eq("id", data.session_id).eq("user_id", user["id"]).eq("status", "active").execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Active session not found")
    
    return {"success": True, "status": "paused"}


@router.post("/session/resume")
async def resume_study_session(
    data: ResumeSessionRequest,
    user: dict = Depends(get_current_user)
):
    """Resume a paused session."""
    supabase = get_supabase_service()
    
    # Get current session to add pause time
    session = supabase.admin_client.table("study_sessions").select("*").eq(
        "id", data.session_id
    ).eq("user_id", user["id"]).single().execute()
    
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_pause = session.data.get("total_pause_seconds", 0) or 0
    
    result = supabase.admin_client.table("study_sessions").update({
        "status": "active",
        "paused_at": None,
        "total_pause_seconds": current_pause + data.pause_duration_seconds,
    }).eq("id", data.session_id).execute()
    
    return {"success": True, "status": "active"}


@router.post("/session/end")
async def end_study_session(
    data: EndSessionRequest,
    user: dict = Depends(get_current_user)
):
    """End a study session and update stats."""
    supabase = get_supabase_service()
    
    # Get session details
    session = supabase.admin_client.table("study_sessions").select("*").eq(
        "id", data.session_id
    ).eq("user_id", user["id"]).single().execute()
    
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_info = session.data
    status = "completed" if data.completed else "cancelled"
    
    # Update session
    supabase.admin_client.table("study_sessions").update({
        "status": status,
        "ended_at": datetime.utcnow().isoformat(),
        "actual_duration_seconds": data.actual_duration_seconds,
        "focus_rating": data.focus_rating,
        "notes": data.notes,
        "distractions_count": data.distractions_count,
    }).eq("id", data.session_id).execute()
    
    # Update daily stats if completed focus session
    if data.completed and session_info["session_type"] == "focus":
        await _update_daily_stats(
            supabase, 
            user["id"], 
            data.actual_duration_seconds,
            data.focus_rating,
            data.distractions_count,
            session_info.get("subject_id")
        )
        
        # Update streak
        await _update_streak(supabase, user["id"])
    
    return {
        "success": True,
        "status": status,
        "duration_seconds": data.actual_duration_seconds,
    }


@router.get("/session/active")
async def get_active_session(user: dict = Depends(get_current_user)):
    """Get currently active session if any."""
    supabase = get_supabase_service()
    
    result = supabase.admin_client.table("study_sessions").select(
        "*, subjects(name)"
    ).eq("user_id", user["id"]).in_("status", ["active", "paused"]).execute()
    
    if result.data:
        session = result.data[0]
        return {
            "has_active": True,
            "session": {
                "id": session["id"],
                "session_type": session["session_type"],
                "duration_minutes": session["duration_minutes"],
                "status": session["status"],
                "started_at": session["started_at"],
                "paused_at": session.get("paused_at"),
                "total_pause_seconds": session.get("total_pause_seconds", 0),
                "subject_name": session.get("subjects", {}).get("name") if session.get("subjects") else None,
                "activity_type": session.get("activity_type"),
            }
        }
    
    return {"has_active": False, "session": None}


# ============ Stats Endpoints ============

@router.get("/stats/today")
async def get_today_stats(user: dict = Depends(get_current_user)):
    """Get today's study statistics."""
    supabase = get_supabase_service()
    today = date.today().isoformat()
    
    # Get daily stats
    stats = supabase.admin_client.table("daily_study_stats").select("*").eq(
        "user_id", user["id"]
    ).eq("date", today).execute()
    
    # Get settings for goal
    settings = supabase.admin_client.table("timer_settings").select(
        "daily_goal_minutes"
    ).eq("user_id", user["id"]).execute()
    
    daily_goal = 120
    if settings.data:
        daily_goal = settings.data[0].get("daily_goal_minutes", 120)
    
    if stats.data:
        s = stats.data[0]
        return {
            "date": today,
            "total_focus_minutes": s.get("total_focus_minutes", 0),
            "total_break_minutes": s.get("total_break_minutes", 0),
            "sessions_completed": s.get("sessions_completed", 0),
            "average_focus_rating": float(s.get("average_focus_rating", 0) or 0),
            "total_distractions": s.get("total_distractions", 0),
            "longest_streak_minutes": s.get("longest_streak_minutes", 0),
            "daily_goal_minutes": daily_goal,
            "goal_progress": min(100, round(s.get("total_focus_minutes", 0) / daily_goal * 100, 1)),
            "goal_achieved": s.get("goal_achieved", False),
        }
    
    return {
        "date": today,
        "total_focus_minutes": 0,
        "total_break_minutes": 0,
        "sessions_completed": 0,
        "average_focus_rating": 0,
        "total_distractions": 0,
        "longest_streak_minutes": 0,
        "daily_goal_minutes": daily_goal,
        "goal_progress": 0,
        "goal_achieved": False,
    }


@router.get("/stats/week")
async def get_week_stats(user: dict = Depends(get_current_user)):
    """Get this week's study statistics."""
    supabase = get_supabase_service()
    
    # Get last 7 days
    today = date.today()
    week_ago = (today - timedelta(days=6)).isoformat()
    
    stats = supabase.admin_client.table("daily_study_stats").select("*").eq(
        "user_id", user["id"]
    ).gte("date", week_ago).order("date").execute()
    
    # Build daily breakdown
    daily_data = []
    total_minutes = 0
    total_sessions = 0
    
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_str = day.isoformat()
        day_stats = next((s for s in (stats.data or []) if s["date"] == day_str), None)
        
        minutes = day_stats.get("total_focus_minutes", 0) if day_stats else 0
        sessions = day_stats.get("sessions_completed", 0) if day_stats else 0
        
        daily_data.append({
            "date": day_str,
            "day": day.strftime("%a"),
            "minutes": minutes,
            "sessions": sessions,
        })
        total_minutes += minutes
        total_sessions += sessions
    
    # Get streak
    streak = supabase.admin_client.table("study_streaks").select("*").eq(
        "user_id", user["id"]
    ).execute()
    
    current_streak = 0
    longest_streak = 0
    if streak.data:
        current_streak = streak.data[0].get("current_streak", 0)
        longest_streak = streak.data[0].get("longest_streak", 0)
    
    return {
        "daily_breakdown": daily_data,
        "total_minutes": total_minutes,
        "total_sessions": total_sessions,
        "average_daily_minutes": round(total_minutes / 7, 1),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
    }


@router.get("/stats/subjects")
async def get_subject_stats(user: dict = Depends(get_current_user)):
    """Get study time breakdown by subject."""
    supabase = get_supabase_service()
    
    # Get last 30 days of subject time
    month_ago = (date.today() - timedelta(days=30)).isoformat()
    
    result = supabase.admin_client.table("subject_study_time").select(
        "subject_id, focus_minutes, subjects(name, color)"
    ).eq("user_id", user["id"]).gte("date", month_ago).execute()
    
    # Aggregate by subject
    subject_totals = {}
    for record in result.data or []:
        sid = record["subject_id"]
        if sid not in subject_totals:
            subject_totals[sid] = {
                "subject_id": sid,
                "name": record.get("subjects", {}).get("name", "Unknown") if record.get("subjects") else "Unknown",
                "color": record.get("subjects", {}).get("color", "#6366F1") if record.get("subjects") else "#6366F1",
                "total_minutes": 0,
            }
        subject_totals[sid]["total_minutes"] += record.get("focus_minutes", 0)
    
    subjects = sorted(subject_totals.values(), key=lambda x: x["total_minutes"], reverse=True)
    
    return {"subjects": subjects}


@router.get("/history")
async def get_session_history(
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    """Get study session history."""
    supabase = get_supabase_service()
    
    result = supabase.admin_client.table("study_sessions").select(
        "*, subjects(name)"
    ).eq("user_id", user["id"]).eq("session_type", "focus").eq(
        "status", "completed"
    ).order("started_at", desc=True).range(offset, offset + limit - 1).execute()
    
    sessions = [
        {
            "id": s["id"],
            "duration_minutes": round(s.get("actual_duration_seconds", 0) / 60, 1),
            "subject_name": s.get("subjects", {}).get("name") if s.get("subjects") else None,
            "activity_type": s.get("activity_type"),
            "focus_rating": s.get("focus_rating"),
            "started_at": s["started_at"],
            "ended_at": s.get("ended_at"),
        }
        for s in result.data or []
    ]
    
    return {"sessions": sessions, "count": len(sessions)}


# ============ Helper Functions ============

async def _update_daily_stats(
    supabase, 
    user_id: str, 
    duration_seconds: int,
    focus_rating: Optional[int],
    distractions: int,
    subject_id: Optional[str]
):
    """Update daily study statistics."""
    today = date.today().isoformat()
    duration_minutes = duration_seconds // 60
    
    # Get or create daily stats
    existing = supabase.admin_client.table("daily_study_stats").select("*").eq(
        "user_id", user_id
    ).eq("date", today).execute()
    
    # Get daily goal
    settings = supabase.admin_client.table("timer_settings").select(
        "daily_goal_minutes"
    ).eq("user_id", user_id).execute()
    daily_goal = settings.data[0].get("daily_goal_minutes", 120) if settings.data else 120
    
    if existing.data:
        stats = existing.data[0]
        new_total = stats.get("total_focus_minutes", 0) + duration_minutes
        new_sessions = stats.get("sessions_completed", 0) + 1
        new_distractions = stats.get("total_distractions", 0) + distractions
        
        # Calculate new average rating
        old_avg = float(stats.get("average_focus_rating", 0) or 0)
        old_count = stats.get("sessions_completed", 0)
        if focus_rating and old_count > 0:
            new_avg = ((old_avg * old_count) + focus_rating) / new_sessions
        elif focus_rating:
            new_avg = focus_rating
        else:
            new_avg = old_avg
        
        supabase.admin_client.table("daily_study_stats").update({
            "total_focus_minutes": new_total,
            "sessions_completed": new_sessions,
            "total_distractions": new_distractions,
            "average_focus_rating": round(new_avg, 2),
            "goal_achieved": new_total >= daily_goal,
            "longest_streak_minutes": max(stats.get("longest_streak_minutes", 0), duration_minutes),
        }).eq("id", stats["id"]).execute()
    else:
        supabase.admin_client.table("daily_study_stats").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "date": today,
            "total_focus_minutes": duration_minutes,
            "sessions_completed": 1,
            "total_distractions": distractions,
            "average_focus_rating": focus_rating,
            "daily_goal_minutes": daily_goal,
            "goal_achieved": duration_minutes >= daily_goal,
            "longest_streak_minutes": duration_minutes,
        }).execute()
    
    # Update subject time if subject provided
    if subject_id:
        subject_existing = supabase.admin_client.table("subject_study_time").select("*").eq(
            "user_id", user_id
        ).eq("subject_id", subject_id).eq("date", today).execute()
        
        if subject_existing.data:
            supabase.admin_client.table("subject_study_time").update({
                "focus_minutes": subject_existing.data[0].get("focus_minutes", 0) + duration_minutes,
                "sessions_count": subject_existing.data[0].get("sessions_count", 0) + 1,
            }).eq("id", subject_existing.data[0]["id"]).execute()
        else:
            supabase.admin_client.table("subject_study_time").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "subject_id": subject_id,
                "date": today,
                "focus_minutes": duration_minutes,
                "sessions_count": 1,
            }).execute()


async def _update_streak(supabase, user_id: str):
    """Update user's study streak."""
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    today_str = today.isoformat()
    
    # Get current streak data
    streak = supabase.admin_client.table("study_streaks").select("*").eq(
        "user_id", user_id
    ).execute()
    
    if streak.data:
        s = streak.data[0]
        last_study = s.get("last_study_date")
        current = s.get("current_streak", 0)
        longest = s.get("longest_streak", 0)
        
        if last_study == today_str:
            # Already studied today, no update needed
            return
        elif last_study == yesterday:
            # Continuing streak
            new_streak = current + 1
            supabase.admin_client.table("study_streaks").update({
                "current_streak": new_streak,
                "longest_streak": max(longest, new_streak),
                "last_study_date": today_str,
            }).eq("user_id", user_id).execute()
        else:
            # Streak broken, start new
            supabase.admin_client.table("study_streaks").update({
                "current_streak": 1,
                "last_study_date": today_str,
                "streak_start_date": today_str,
            }).eq("user_id", user_id).execute()
    else:
        # First time studying
        supabase.admin_client.table("study_streaks").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_study_date": today_str,
            "streak_start_date": today_str,
        }).execute()
