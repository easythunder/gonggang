# Frontend-Backend API Mapping

## Backend Endpoints Summary

### Groups API (`/groups`)
| Method | Endpoint | Request | Response | Purpose |
|--------|----------|---------|----------|---------|
| POST | `/groups` | CreateGroupRequest | `{status, data, message}` | Create new group |
| GET | `/groups/{group_id}` | - | `{status, data}` | Get group details |
| GET | `/groups/{group_id}/share` | - | `{status, data}` | Get share info |

### Submissions API (`/api`)
| Method | Endpoint | Request | Response | Purpose |
|--------|----------|---------|----------|---------|
| POST | `/api/submissions` | FormData (group_id, nickname, image) | JSON | Submit schedule image |
| GET | `/api/submissions/{submission_id}` | - | JSON | Get submission details |
| GET | `/api/groups/{group_id}/submissions` | - | JSON | Get all submissions in group |

### Free-Time API (`/groups`)
| Method | Endpoint | Request | Response | Purpose |
|--------|----------|---------|----------|---------|
| GET | `/groups/{group_id}/free-time` | - | `{group_id, group_name, participants, free_time, ...}` | Get common free time |
| GET | `/groups/{group_id}` | - | `{status, data}` | Get group info |
| GET | `/groups/{group_id}/view` | - | HTML | Render group view |

---

## Frontend API Calls Mapping

### 1. Sample Group Creation (Welcome Screen)
**Frontend Call:**
```javascript
const res = await fetch(`${API_BASE}/groups`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        group_name: 'Sample Group',
        display_unit_minutes: 30 
    })
});
const data = await res.json();
this.sampleGroupId = data.data.group_id;
```

**Backend Endpoint:** `POST /groups`
**Request Format:**
```json
{
    "group_name": "string (optional)",
    "display_unit_minutes": 30
}
```
**Response Format:**
```json
{
    "status": "success",
    "data": {
        "group_id": "uuid-string",
        "group_name": "string",
        "created_at": "ISO-8601",
        "expires_at": "ISO-8601",
        "invite_url": "string",
        "share_url": "string",
        "display_unit_minutes": 30,
        "max_participants": "integer"
    },
    "message": "Group created successfully"
}
```
**Status:** ✅ Correctly mapped

---

### 2. Create Group (Create Group Screen)
**Frontend Call:**
```javascript
const createRes = await fetch(`${API_BASE}/groups`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        group_name: groupNameInput,
        display_unit_minutes: displayUnit 
    })
});
const groupData = await createRes.json();
this.groupId = groupData.data.group_id;
```

**Backend Endpoint:** `POST /groups`
**Status:** ✅ Correctly mapped (Same as #1)

---

### 3. Validate Group (Join Group Screen)
**Frontend Call:**
```javascript
const res = await fetch(`${API_BASE}/groups/${groupId}`);
if (res.ok) {
    this.groupId = groupId;
    // Show form...
}
```

**Backend Endpoint:** `GET /groups/{group_id}`
**Response Format:**
```json
{
    "status": "success",
    "data": {
        "group_id": "uuid-string",
        "group_name": "string",
        "created_at": "ISO-8601",
        "expires_at": "ISO-8601",
        "invite_url": "string",
        "share_url": "string",
        "display_unit_minutes": 30,
        "max_participants": "integer"
    }
}
```
**Status:** ✅ Correctly mapped

---

### 4. Submit Schedule Image (Create Group + Join Group)
**Frontend Call:**
```javascript
const formData = new FormData();
formData.append('group_id', this.groupId);
formData.append('nickname', this.currentNickname);
formData.append('image', this.scheduleFile);

const submitRes = await fetch(`${API_BASE}/api/submissions`, {
    method: 'POST',
    body: formData
});
const submitData = await submitRes.json();
```

**Backend Endpoint:** `POST /api/submissions`
**Request Format:** FormData with:
- `group_id`: UUID string
- `nickname`: String (1-50 characters)
- `image`: Binary file

**Response Format (201):**
```json
{
    "submission_id": "uuid-string",
    "nickname": "string",
    "group_id": "uuid-string",
    "status": "SUCCESS" or "FAILED",
    "interval_count": integer,
    "created_at": "ISO-8601"
}
```

**Response Format (409 - Duplicate):**
```json
{
    "detail": "Nickname 'xxx' already submitted for this group"
}
```

**Status:** ✅ Correctly mapped

---

### 5. Get Group Info (After Submission)
**Frontend Call:**
```javascript
const groupRes = await fetch(`${API_BASE}/groups/${this.groupId}`);
const groupData = await groupRes.json();
this.showResults(this.groupId, groupData);
```

**Backend Endpoint:** `GET /groups/{group_id}`
**Status:** ✅ Correctly mapped (Same as #3)

---

### 6. Get Free Time Results (Results Screen)
**Frontend Call:**
```javascript
const res = await fetch(`${API_BASE}/groups/${groupId}/free-time`);
const data = await res.json();
// data.group_id, data.free_time, data.participants, data.participant_count
```

**Backend Endpoint:** `GET /groups/{group_id}/free-time`
**Response Format (Direct - NOT wrapped in `{status, data}`):**
```json
{
    "group_id": "uuid-string",
    "group_name": "string",
    "participant_count": integer,
    "participants": [
        {
            "nickname": "string",
            "submitted_at": "ISO-8601"
        }
    ],
    "free_time": [
        {
            "day": "MONDAY|TUESDAY|...",
            "start_minute": integer,
            "end_minute": integer,
            "duration_minutes": integer,
            "overlap_count": integer
        }
    ],
    "free_time_30min": [...],
    "free_time_60min": [...],
    "availability_by_day": {...},
    "computed_at": "ISO-8601 or null",
    "expires_at": "ISO-8601",
    "display_unit_minutes": integer,
    "version": integer
}
```

**Status:** ✅ Correctly mapped (FIXED in previous update)

---

## Summary of Findings

| # | Feature | Endpoint | Frontend Code | Status |
|---|---------|----------|----------------|--------|
| 1 | Sample group creation | POST /groups | line ~710 | ✅ OK |
| 2 | Create group | POST /groups | line ~813 | ✅ OK |
| 3 | Validate join group | GET /groups/{id} | line ~920 | ✅ OK |
| 4 | Submit schedule | POST /api/submissions | line ~881, ~972 | ✅ OK |
| 5 | Get group info | GET /groups/{id} | line ~893, ~984 | ✅ OK |
| 6 | Get free-time | GET /groups/{id}/free-time | line ~1053 | ✅ FIXED |

---

## Implementation Notes

### Response Structure Differences
- **Groups API**: Wrapped in `{status, data, message}`
  - Access via: `response.data.field`
- **Submissions API**: Direct response (NOT wrapped)
  - Access via: `response.field`
- **Free-Time API**: Direct response (NOT wrapped)
  - Access via: `response.field`

### Error Handling
- **404 Not Found**: Group doesn't exist
- **409 Conflict**: Nickname duplicate
- **410 Gone**: Group expired
- **422 Unprocessable**: Invalid input (UUID format, nickname length, etc.)

### Important Fields
- `group_id` should always be UUID format when sending
- `display_unit_minutes` default is 30, must be in [10, 20, 30, 60]
- `nickname` limited to 1-50 characters
- Timestamps are ISO-8601 format
