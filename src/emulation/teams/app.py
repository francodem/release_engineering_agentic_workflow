from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import os

app = FastAPI(title="Teams Clone API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Mount static files directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory database
posts_db = []
replies_db = []

# Initialize with sample data
def init_sample_data():
    """Initialize with sample post data"""
    if not posts_db:  # Only add if database is empty
        sample_post = {
            "id": str(uuid.uuid4()),
            "title": "M190.0.0 Google Vertex AI Release",
            "user": "Cristina M.",
            "role": "Program Manager",
            "message": "Hello everyone, this is the deployment plan to start today with it. Please check the component ID here: vertex-ai-re-agent.",
            "timestamp": datetime.now().isoformat()
        }
        posts_db.append(sample_post)
        
        # Add sample reply to the post
        sample_reply = {
            "id": str(uuid.uuid4()),
            "post_id": sample_post["id"],
            "user": "Alexa A.",
            "role": "SCRUM Master",
            "message": "M190.0.0 GVA validated.\n\nThere is no pending SC tickets.\n\nPlease start with the release.",
            "timestamp": datetime.now().isoformat()
        }
        replies_db.append(sample_reply)

# Initialize sample data on startup
init_sample_data()


# Models
class PostCreate(BaseModel):
    title: Optional[str] = None
    user: str
    role: str
    message: str


class PostUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None


class ReplyCreate(BaseModel):
    post_id: str
    user: str
    role: str
    message: str


class ReplyCreateSimple(BaseModel):
    """Simplified reply creation without post_id (post_id comes from URL)"""
    user: str
    role: str
    message: str


class ReplyUpdate(BaseModel):
    message: str


class Post(BaseModel):
    id: str
    title: Optional[str] = None
    user: str
    role: str
    message: str
    timestamp: str
    replies: List[dict] = []


class Reply(BaseModel):
    id: str
    post_id: str
    user: str
    role: str
    message: str
    timestamp: str


class PostSummary(BaseModel):
    """Simplified post model for list view (no replies)"""
    id: str
    title: Optional[str] = None
    message: str


# API Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    template_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/posts", response_model=List[PostSummary])
async def get_posts():
    """Get all posts - returns id, title, and message (without replies)"""
    return [
        PostSummary(id=post["id"], title=post.get("title"), message=post["message"])
        for post in posts_db
    ]


@app.get("/api/posts/full", response_model=List[Post])
async def get_posts_full():
    """Get all posts with their replies - for frontend use"""
    try:
        posts_with_replies = []
        for post in posts_db:
            post_replies = [reply for reply in replies_db if reply["post_id"] == post["id"]]
            post_dict = {
                "id": post["id"],
                "title": post.get("title"),
                "user": post["user"],
                "role": post["role"],
                "message": post["message"],
                "timestamp": post["timestamp"],
                "replies": post_replies
            }
            posts_with_replies.append(post_dict)
        return posts_with_replies
    except Exception as e:
        print(f"Error in get_posts_full: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/posts/{post_id}", response_model=Post)
async def get_post(post_id: str):
    """Get a specific post with its replies"""
    post = next((p for p in posts_db if p["id"] == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post_replies = [reply for reply in replies_db if reply["post_id"] == post_id]
    post_dict = post.copy()
    post_dict["replies"] = post_replies
    return post_dict


@app.get("/api/posts/{post_id}/replies", response_model=List[Reply])
async def get_replies(post_id: str):
    """Get all replies for a specific post"""
    replies = [reply for reply in replies_db if reply["post_id"] == post_id]
    return replies


@app.post("/api/posts")
async def create_post(post: PostCreate):
    """Create a new post"""
    new_post = {
        "id": str(uuid.uuid4()),
        "title": post.title,
        "user": post.user,
        "role": post.role,
        "message": post.message,
        "timestamp": datetime.now().isoformat()
    }
    posts_db.append(new_post)
    return new_post


@app.put("/api/posts/{post_id}")
async def update_post(post_id: str, post_update: PostUpdate):
    """Update a post"""
    post = next((p for p in posts_db if p["id"] == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post_update.title is not None:
        post["title"] = post_update.title
    if post_update.message is not None:
        post["message"] = post_update.message
    post["timestamp"] = datetime.now().isoformat()
    return post


@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: str):
    """Delete a post and all its replies"""
    post = next((p for p in posts_db if p["id"] == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    posts_db.remove(post)
    # Delete all replies for this post
    replies_db[:] = [r for r in replies_db if r["post_id"] != post_id]
    return {"message": "Post deleted successfully"}


@app.post("/api/replies")
async def create_reply(reply: ReplyCreate):
    """Create a new reply to a post (requires post_id in body)"""
    # Verify post exists
    post = next((p for p in posts_db if p["id"] == reply.post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    new_reply = {
        "id": str(uuid.uuid4()),
        "post_id": reply.post_id,
        "user": reply.user,
        "role": reply.role,
        "message": reply.message,
        "timestamp": datetime.now().isoformat()
    }
    replies_db.append(new_reply)
    return new_reply


@app.post("/api/posts/{post_id}/replies")
async def create_reply_simple(post_id: str, reply: ReplyCreateSimple):
    """Create a new reply to a post (post_id from URL, simplified body with user, role, message)"""
    # Verify post exists
    post = next((p for p in posts_db if p["id"] == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    new_reply = {
        "id": str(uuid.uuid4()),
        "post_id": post_id,
        "user": reply.user,
        "role": reply.role,
        "message": reply.message,
        "timestamp": datetime.now().isoformat()
    }
    replies_db.append(new_reply)
    return new_reply


@app.put("/api/replies/{reply_id}")
async def update_reply(reply_id: str, reply_update: ReplyUpdate):
    """Update a reply"""
    reply = next((r for r in replies_db if r["id"] == reply_id), None)
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    
    reply["message"] = reply_update.message
    reply["timestamp"] = datetime.now().isoformat()
    return reply


@app.delete("/api/replies/{reply_id}")
async def delete_reply(reply_id: str):
    """Delete a reply"""
    reply = next((r for r in replies_db if r["id"] == reply_id), None)
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    
    replies_db.remove(reply)
    return {"message": "Reply deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
