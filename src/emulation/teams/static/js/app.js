// Teams Clone - JavaScript

const API_BASE = '/api';

// DOM Elements
const postsContainer = document.getElementById('posts-container');
const newPostForm = document.getElementById('new-post-form');
const editModal = document.getElementById('edit-modal');
const editForm = document.getElementById('edit-form');
const closeModal = document.querySelector('.close');

// Initialize
let lastUpdateTime = null;
let pollingInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
    await initializeState();
    loadPosts();
    setupEventListeners();
    startPolling();
});

// Start polling for updates
function startPolling() {
    // Poll every 3 seconds for new posts/replies
    pollingInterval = setInterval(() => {
        checkForUpdates();
    }, 3000);
}

// Stop polling (useful when page is hidden)
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Store last known state for comparison
let lastKnownState = {
    postIds: new Set(),
    replyCounts: {}
};

// Check for updates
async function checkForUpdates() {
    try {
        // Get all posts with replies for comparison
        const posts = await loadAllPostsWithReplies();
        
        // Get current state
        const currentPostIds = new Set(posts.map(p => p.id));
        const currentReplyCounts = {};
        posts.forEach(post => {
            currentReplyCounts[post.id] = (post.replies || []).length;
        });
        
        // Check if there are new posts
        const hasNewPosts = currentPostIds.size !== lastKnownState.postIds.size ||
                           ![...currentPostIds].every(id => lastKnownState.postIds.has(id)) ||
                           ![...lastKnownState.postIds].every(id => currentPostIds.has(id));
        
        // Check if there are new replies
        let hasNewReplies = false;
        if (!hasNewPosts) {
            for (const postId of currentPostIds) {
                const currentCount = currentReplyCounts[postId] || 0;
                const lastCount = lastKnownState.replyCounts[postId] || 0;
                if (currentCount !== lastCount) {
                    hasNewReplies = true;
                    break;
                }
            }
        }
        
        // Only reload if there are changes (but don't update state yet, let loadPosts do it)
        if (hasNewPosts || hasNewReplies) {
            loadPosts();
        } else {
            // No changes detected, update state
            lastKnownState.postIds = new Set(currentPostIds);
            lastKnownState.replyCounts = {...currentReplyCounts};
        }
    } catch (error) {
        console.error('Error checking for updates:', error);
    }
}

// Initialize last known state on first load
async function initializeState() {
    try {
        const posts = await loadAllPostsWithReplies();
        updateLastKnownState(posts);
    } catch (error) {
        console.error('Error initializing state:', error);
    }
}

// Event Listeners
function setupEventListeners() {
    newPostForm.addEventListener('submit', handleCreatePost);
    editForm.addEventListener('submit', handleUpdatePost);
    closeModal.addEventListener('click', () => {
        editModal.style.display = 'none';
    });
    
    window.addEventListener('click', (event) => {
        if (event.target === editModal) {
            editModal.style.display = 'none';
        }
    });
    
    // New post trigger
    const newPostTrigger = document.getElementById('new-post-trigger');
    if (newPostTrigger) {
        newPostTrigger.addEventListener('click', () => {
            document.getElementById('new-post-form-container').style.display = 'block';
            newPostTrigger.style.display = 'none';
        });
    }
    
    // Post and Announcement buttons
    const btnPost = document.querySelector('.btn-post');
    const btnAnnouncement = document.querySelector('.btn-announcement');
    
    if (btnPost) {
        btnPost.addEventListener('click', () => {
            document.getElementById('new-post-form-container').style.display = 'block';
            document.getElementById('new-post-trigger').style.display = 'none';
        });
    }
    
    if (btnAnnouncement) {
        btnAnnouncement.addEventListener('click', () => {
            document.getElementById('new-post-form-container').style.display = 'block';
            document.getElementById('new-post-trigger').style.display = 'none';
        });
    }
}

// Load all posts with their replies
async function loadAllPostsWithReplies() {
    try {
        // Use the full posts endpoint for frontend
        const response = await fetch(`${API_BASE}/posts/full`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`HTTP error! status: ${response.status}, body: ${errorText}`);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        const posts = await response.json();
        
        // Validate response is an array
        if (!Array.isArray(posts)) {
            console.error('Invalid response format:', posts);
            throw new Error('Invalid response format: expected array');
        }
        
        // If no posts, return empty array
        if (posts.length === 0) {
            return [];
        }
        
        return posts;
    } catch (error) {
        console.error('Error loading posts with replies:', error);
        console.error('Error stack:', error.stack);
        throw error;
    }
}

// Load Posts
async function loadPosts() {
    try {
        const posts = await loadAllPostsWithReplies();
        displayPosts(posts);
        // Update last known state after loading
        updateLastKnownState(posts);
    } catch (error) {
        console.error('Error loading posts:', error);
        console.error('Error details:', error.message, error.stack);
        postsContainer.innerHTML = '<div class="empty-state"><h3>Error loading posts</h3><p>Please try again later.</p><p style="font-size: 12px; color: #8a8886;">Error: ' + error.message + '</p></div>';
    }
}

// Update last known state
function updateLastKnownState(posts) {
    lastKnownState.postIds = new Set(posts.map(p => p.id));
    lastKnownState.replyCounts = {};
    posts.forEach(post => {
        lastKnownState.replyCounts[post.id] = (post.replies || []).length;
    });
}

// Display Posts
function displayPosts(posts) {
    if (posts.length === 0) {
        postsContainer.innerHTML = '<div class="empty-state"><h3>No posts yet</h3><p>Start a new conversation!</p></div>';
        return;
    }
    
    // Sort posts by timestamp (newest first)
    const sortedPosts = [...posts].sort((a, b) => {
        return new Date(b.timestamp) - new Date(a.timestamp);
    });
    
    postsContainer.innerHTML = sortedPosts.map(post => createPostHTML(post)).join('');
    
    // Attach event listeners to reply forms
    attachReplyListeners();
}

// Create Post HTML
function createPostHTML(post) {
    const timestamp = formatTimestamp(post.timestamp);
    const avatar = post.user.charAt(0).toUpperCase();
    const replies = post.replies || [];
    const escapedMessage = escapeHtml(post.message).replace(/'/g, "\\'").replace(/\n/g, '\\n');
    const escapedTitle = post.title ? escapeHtml(post.title).replace(/'/g, "\\'").replace(/\n/g, '\\n') : '';
    
    let html = `
        <div class="post-card" data-post-id="${post.id}">
            <div class="post-header">
                <div class="post-avatar">${avatar}</div>
                <div class="post-info">
                    <div class="post-author">
                        <span class="post-author-name">${escapeHtml(post.user)}</span>
                        <span class="post-author-role">${escapeHtml(post.role)}</span>
                    </div>
                    <div class="post-timestamp">${timestamp}</div>
                    ${post.title ? `<h3 class="post-title">${escapeHtml(post.title)}</h3>` : ''}
                    <div class="post-message">${escapeHtml(post.message)}</div>
                    <div class="post-actions">
                        <div class="reaction-btn">
                            <span class="reaction-icon">👍</span>
                            <span>0</span>
                        </div>
                        <div class="reaction-btn">
                            <span class="reaction-icon">❤️</span>
                            <span>0</span>
                        </div>
                        <div class="reaction-btn">
                            <span class="reaction-icon">😄</span>
                            <span>0</span>
                        </div>
                        ${replies.length > 0 ? `
                            <a href="#" class="replies-link">${replies.length} ${replies.length === 1 ? 'reply' : 'replies'} from ${getReplyAuthors(replies)}</a>
                        ` : ''}
                        <div class="action-buttons">
                            <button class="btn-action edit" onclick="openEditModal('${post.id}', 'post', \`${escapedMessage}\`, \`${escapedTitle}\`)">Edit</button>
                            <button class="btn-action delete" onclick="deletePost('${post.id}')">Delete</button>
                        </div>
                    </div>
                </div>
            </div>
    `;
    
    if (replies.length > 0) {
        // Sort replies by timestamp (oldest first, like a conversation)
        const sortedReplies = [...replies].sort((a, b) => {
            return new Date(a.timestamp) - new Date(b.timestamp);
        });
        
        html += `
            <div class="replies-section">
                <div class="replies-header">${replies.length} ${replies.length === 1 ? 'reply' : 'replies'}</div>
                ${sortedReplies.map(reply => createReplyHTML(reply)).join('')}
            </div>
        `;
    }
    
    html += `
            <div class="reply-form">
                <form class="reply-form-content" data-post-id="${post.id}">
                    <div class="reply-form-inputs">
                        <input type="text" name="user" placeholder="Your name" required>
                        <input type="text" name="role" placeholder="Your role" required>
                    </div>
                    <textarea name="message" placeholder="Type a reply..." required></textarea>
                    <button type="submit" class="btn-reply">Reply</button>
                </form>
            </div>
        </div>
    `;
    
    return html;
}

// Get reply authors for display
function getReplyAuthors(replies) {
    const authors = replies.slice(0, 3).map(r => escapeHtml(r.user));
    if (replies.length > 3) {
        return authors.join(', ') + `, and ${replies.length - 3} others`;
    }
    return authors.join(', ');
}

// Create Reply HTML
function createReplyHTML(reply) {
    const timestamp = formatTimestamp(reply.timestamp);
    const avatar = reply.user.charAt(0).toUpperCase();
    const escapedMessage = escapeHtml(reply.message).replace(/'/g, "\\'").replace(/\n/g, '\\n');
    
    return `
        <div class="reply-card" data-reply-id="${reply.id}" data-post-id="${reply.post_id}">
            <div class="reply-avatar">${avatar}</div>
            <div class="reply-info">
                <div class="reply-author">
                    <span class="reply-author-name">${escapeHtml(reply.user)}</span>
                    <span class="reply-author-role">${escapeHtml(reply.role)}</span>
                </div>
                <div class="reply-timestamp">${timestamp}</div>
                <div class="reply-message">${escapeHtml(reply.message)}</div>
                <div class="reply-actions">
                    <button class="btn-action edit" onclick="openEditModal('${reply.id}', 'reply', \`${escapedMessage}\`)">Edit</button>
                    <button class="btn-action delete" onclick="deleteReply('${reply.id}')">Delete</button>
                </div>
            </div>
        </div>
    `;
}

// Attach Reply Listeners
function attachReplyListeners() {
    const replyForms = document.querySelectorAll('.reply-form-content');
    replyForms.forEach(form => {
        form.addEventListener('submit', handleCreateReply);
    });
}

// Handle Create Post
async function handleCreatePost(event) {
    event.preventDefault();
    const postTitle = document.getElementById('post-title').value.trim();
    const userName = document.getElementById('user-name').value;
    const userRole = document.getElementById('user-role').value;
    const postMessage = document.getElementById('post-message').value;
    
    if (!userName || !userRole || !postMessage) {
        alert('Please fill in all required fields');
        return;
    }
    
    const postData = {
        title: postTitle || null,
        user: userName,
        role: userRole,
        message: postMessage
    };
    
    try {
        const response = await fetch(`${API_BASE}/posts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(postData)
        });
        
        if (response.ok) {
            document.getElementById('new-post-form').reset();
            document.getElementById('new-post-form-container').style.display = 'none';
            document.getElementById('new-post-trigger').style.display = 'block';
            loadPosts();
        } else {
            alert('Error creating post. Please try again.');
        }
    } catch (error) {
        console.error('Error creating post:', error);
        alert('Error creating post. Please try again.');
    }
}

// Cancel new post
function cancelNewPost() {
    document.getElementById('new-post-form-container').style.display = 'none';
    document.getElementById('new-post-trigger').style.display = 'block';
    document.getElementById('new-post-form').reset();
}

// Handle Create Reply
async function handleCreateReply(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const postId = event.target.getAttribute('data-post-id');
    const replyData = {
        user: formData.get('user'),
        role: formData.get('role'),
        message: formData.get('message')
    };
    
    if (!replyData.user || !replyData.role || !replyData.message) {
        alert('Please fill in all reply fields.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/posts/${postId}/replies`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(replyData)
        });
        
        if (response.ok) {
            event.target.reset();
            loadPosts();
        } else {
            const errorText = await response.text();
            console.error('Error creating reply:', response.status, errorText);
            alert('Error creating reply. Please try again.');
        }
    } catch (error) {
        console.error('Error creating reply:', error);
        alert('Error creating reply. Please try again.');
    }
}

// Open Edit Modal
function openEditModal(id, type, message, title = '') {
    document.getElementById('edit-id').value = id;
    document.getElementById('edit-type').value = type;
    document.getElementById('edit-message').value = message;
    // Note: For simplicity, we're only editing the message in the modal
    // Title editing could be added later if needed
    editModal.style.display = 'block';
}

// Handle Update Post/Reply
async function handleUpdatePost(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const id = formData.get('id');
    const type = formData.get('type');
    const message = formData.get('message');
    
    try {
        const endpoint = type === 'post' ? `${API_BASE}/posts/${id}` : `${API_BASE}/replies/${id}`;
        const response = await fetch(endpoint, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        
        if (response.ok) {
            editModal.style.display = 'none';
            loadPosts();
        } else {
            alert('Error updating message. Please try again.');
        }
    } catch (error) {
        console.error('Error updating message:', error);
        alert('Error updating message. Please try again.');
    }
}

// Delete Post
async function deletePost(postId) {
    if (!confirm('Are you sure you want to delete this post? This will also delete all replies.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/posts/${postId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadPosts();
        } else {
            alert('Error deleting post. Please try again.');
        }
    } catch (error) {
        console.error('Error deleting post:', error);
        alert('Error deleting post. Please try again.');
    }
}

// Delete Reply
async function deleteReply(replyId) {
    if (!confirm('Are you sure you want to delete this reply?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/replies/${replyId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadPosts();
        } else {
            alert('Error deleting reply. Please try again.');
        }
    } catch (error) {
        console.error('Error deleting reply:', error);
        alert('Error deleting reply. Please try again.');
    }
}

// Utility Functions
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) {
        return 'Just now';
    } else if (minutes < 60) {
        return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
    } else if (hours < 24) {
        return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
    } else if (days < 7) {
        return `${days} ${days === 1 ? 'day' : 'days'} ago`;
    } else {
        return date.toLocaleDateString();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally available
window.openEditModal = openEditModal;
window.deletePost = deletePost;
window.deleteReply = deleteReply;
window.cancelNewPost = cancelNewPost;

