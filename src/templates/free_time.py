"""
Frontend template for results display (T061)

HTML template showing:
- Candidate cards (top 5, ranked)
- Weekly grid heatmap with availability percentages
- Participants list with nicknames
"""
import json
from typing import Dict, Any


def render_free_time_template(response_data: Dict[str, Any]) -> str:
    """
    Render HTML template for free-time results.
    
    Args:
        response_data: FreeTimeResponse data dict
    
    Returns:
        str: HTML page
    """
    group_id = response_data.get("group_id", "")
    group_name = response_data.get("group_name", "")
    expires_at = response_data.get("expires_at", "")
    free_time = response_data.get("free_time", [])
    participants = response_data.get("participants", [])
    
    # Convert to minutes to hours:minutes format
    def format_time(minutes: int) -> str:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
    
    # Build candidate cards (sorted by duration)
    candidate_cards_html = ""
    for i, slot in enumerate(free_time[:5], 1):
        duration = slot["duration_minutes"]
        day = slot["day"]
        start = format_time(slot["start_minute"])
        end = format_time(slot["end_minute"])
        overlap = slot["overlap_count"]
        
        candidate_cards_html += f"""
        <div class="candidate-card" data-index="{i}">
            <div class="card-header">Candidate #{i}</div>
            <div class="card-body">
                <div class="day-badge">{day}</div>
                <div class="time-range">{start} - {end}</div>
                <div class="duration-info">{duration} minutes</div>
                <div class="overlap-count">{overlap} people can attend</div>
            </div>
        </div>
        """
    
    # Build participants list
    participants_html = ""
    for participant in participants:
        nickname = participant["nickname"]
        submitted_at = participant["submitted_at"]
        # Parse ISO datetime
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
            time_str = dt.strftime("%m-%d %H:%M")
        except:
            time_str = submitted_at
        
        participants_html += f"""
        <div class="participant-item">
            <span class="nickname">{nickname}</span>
            <span class="submitted-time">{time_str}</span>
        </div>
        """
    
    # Build weekly grid
    days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    grid_html = '<div class="weekly-grid">'
    grid_html += '<div class="grid-header">'
    for day in days:
        grid_html += f'<div class="day-header">{day[:3]}</div>'
    grid_html += '</div>'
    
    # Create time slots (every 30 minutes for simplicity)
    for hour in range(0, 24):
        grid_html += f'<div class="time-row time-{hour}" data-hour="{hour}">'
        grid_html += f'<div class="hour-label">{hour:02d}:00</div>'
        
        for day in days:
            # Check if this slot has availability
            has_availability = False
            overlap_count = 0
            for slot in free_time:
                if slot["day"] == day:
                    start_hour = slot["start_minute"] // 60
                    end_hour = (slot["end_minute"] - 1) // 60
                    if start_hour <= hour <= end_hour:
                        has_availability = True
                        overlap_count = slot["overlap_count"]
                        break
            
            if has_availability:
                # Color intensity based on overlap count
                intensity = min(100, (overlap_count * 20))
                grid_html += f'<div class="grid-cell available" style="opacity: {intensity/100}" data-overlap="{overlap_count}"></div>'
            else:
                grid_html += f'<div class="grid-cell unavailable"></div>'
        
        grid_html += '</div>'
    
    grid_html += '</div>'
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Free Time Results - {{group_name}}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 30px;
            }}
            
            h1 {{
                color: #333;
                margin-bottom: 10px;
            }}
            
            .group-info {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid #eee;
            }}
            
            .group-meta {{
                font-size: 14px;
                color: #666;
            }}
            
            .expires-banner {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 20px;
                color: #856404;
            }}
            
            .content {{
                display: grid;
                grid-template-columns: 350px 1fr;
                gap: 30px;
                margin-bottom: 30px;
            }}
            
            @media (max-width: 900px) {{
                .content {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            /* Candidate Cards */
            .candidates-section h2 {{
                color: #333;
                font-size: 18px;
                margin-bottom: 15px;
            }}
            
            .candidate-card {{
                background: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 12px;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            .candidate-card:hover {{
                background: #f0f7ff;
                border-color: #0066cc;
                box-shadow: 0 2px 8px rgba(0, 102, 204, 0.15);
            }}
            
            .card-header {{
                font-weight: 600;
                color: #0066cc;
                margin-bottom: 10px;
                font-size: 14px;
            }}
            
            .card-body {{
                font-size: 13px;
            }}
            
            .day-badge {{
                display: inline-block;
                background: #e3f2fd;
                color: #0066cc;
                padding: 3px 8px;
                border-radius: 3px;
                font-weight: 600;
                margin-bottom: 8px;
            }}
            
            .time-range {{
                font-size: 16px;
                font-weight: 600;
                color: #333;
                margin-bottom: 4px;
            }}
            
            .duration-info {{
                color: #666;
                margin-bottom: 4px;
            }}
            
            .overlap-count {{
                color: #28a745;
                font-weight: 500;
            }}
            
            /* Weekly Grid */
            .grid-section h2 {{
                color: #333;
                font-size: 18px;
                margin-bottom: 15px;
            }}
            
            .weekly-grid {{
                overflow-x: auto;
                border: 1px solid #ddd;
                border-radius: 6px;
            }}
            
            .grid-header {{
                display: grid;
                grid-template-columns: 60px repeat(7, 1fr);
                background: #f0f0f0;
                font-weight: 600;
                font-size: 13px;
                text-align: center;
                border-bottom: 2px solid #ddd;
            }}
            
            .day-header {{
                padding: 12px 8px;
                color: #333;
            }}
            
            .time-row {{
                display: grid;
                grid-template-columns: 60px repeat(7, 1fr);
                border-bottom: 1px solid #eee;
                align-items: stretch;
                min-height: 30px;
            }}
            
            .hour-label {{
                padding: 12px 8px;
                font-size: 12px;
                color: #666;
                background: #fafafa;
                text-align: center;
                font-weight: 500;
                border-right: 1px solid #eee;
            }}
            
            .grid-cell {{
                padding: 2px;
                transition: all 0.2s;
            }}
            
            .grid-cell.available {{
                background: linear-gradient(135deg, #4CAF50 0%, #81C784 100%);
                cursor: pointer;
            }}
            
            .grid-cell.available:hover {{
                opacity: 1 !important;
                box-shadow: inset 0 0 0 2px #fff;
            }}
            
            .grid-cell.unavailable {{
                background: #f5f5f5;
            }}
            
            /* Participants */
            .participants-section {{
                grid-column: 1 / -1;
                border-top: 1px solid #eee;
                padding-top: 20px;
            }}
            
            .participants-section h2 {{
                color: #333;
                font-size: 18px;
                margin-bottom: 15px;
            }}
            
            .participants-list {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
            }}
            
            .participant-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                background: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 13px;
            }}
            
            .nickname {{
                font-weight: 600;
                color: #333;
            }}
            
            .submitted-time {{
                color: #999;
                font-size: 12px;
            }}
            
            /* Footer */
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                text-align: center;
                font-size: 12px;
                color: #999;
            }}
            
            .legend {{
                margin-top: 20px;
                padding: 15px;
                background: #f9f9f9;
                border-radius: 4px;
                font-size: 13px;
            }}
            
            .legend-item {{
                display: inline-block;
                margin-right: 20px;
            }}
            
            .legend-color {{
                display: inline-block;
                width: 20px;
                height: 20px;
                border-radius: 2px;
                margin-right: 6px;
                vertical-align: middle;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="group-info">
                <div>
                    <h1>{group_name}</h1>
                    <div class="group-meta">Group ID: {group_id}</div>
                </div>
                <div style="text-align: right;">
                    <div class="group-meta">Expires: {expires_at}</div>
                </div>
            </div>
            
            <div class="expires-banner">
                ⏰ This page will be deleted and data will be purged {expires_at}
            </div>
            
            <div class="content">
                <div class="candidates-section">
                    <h2>Top Meeting Times</h2>
                    {candidate_cards_html if candidate_cards_html else '<p style="color: #999;">No available meeting times found.</p>'}
                </div>
                
                <div class="grid-section">
                    <h2>Weekly Availability</h2>
                    {grid_html}
                    <div class="legend">
                        <div class="legend-item"><span class="legend-color" style="background: #4CAF50;"></span>Available</div>
                        <div class="legend-item"><span class="legend-color" style="background: #f5f5f5; border: 1px solid #ddd;"></span>Busy</div>
                    </div>
                </div>
            </div>
            
            <div class="participants-section">
                <h2>Participants ({len(participants)})</h2>
                <div class="participants-list">
                    {participants_html}
                </div>
            </div>
            
            <div class="footer">
                <p>Gonggang - Find common free time effortlessly</p>
            </div>
        </div>
        
        <script>
            // Click handler for candidate cards
            document.querySelectorAll('.candidate-card').forEach((card, idx) => {{
                card.addEventListener('click', () => {{
                    const index = idx + 1;
                    const slot = document.querySelector('[data-index="' + index + '"]');
                    if (slot) {{
                        slot.style.borderColor = '#0066cc';
                        slot.style.backgroundColor = '#f0f7ff';
                        setTimeout(() => {{
                            slot.style.borderColor = '#e0e0e0';
                            slot.style.backgroundColor = '#f9f9f9';
                        }}, 2000);
                    }}
                }});
            }});
            
            // Auto-refresh polling
            let lastVersion = 0;
            async function pollResults() {{
                try {{
                    const response = await fetch(window.location.pathname + '?format=json');
                    if (response.status === 410) {{
                        document.body.innerHTML = '<div style="padding: 20px;"><h1>This group has expired</h1><p>The shared time has been deleted.</p></div>';
                        return;
                    }}
                    
                    const version = response.headers.get('X-Calculation-Version');
                    if (version && version !== lastVersion) {{
                        lastVersion = version;
                        location.reload();
                    }}
                    
                    const pollWait = parseInt(response.headers.get('X-Poll-Wait') || '3000');
                    setTimeout(pollResults, pollWait);
                }} catch (e) {{
                    console.error('Poll error:', e);
                    setTimeout(pollResults, 3000);
                }}
            }}
            
            // Start polling in background
            setTimeout(pollResults, 5000);
        </script>
    </body>
    </html>
    """
    
    return html.format(group_name=group_name, group_id=group_id, expires_at=expires_at)


def get_html_route(response_data: Dict[str, Any]) -> str:
    """
    Get HTML version of the free-time results.
    Can be used as a fallback when Accept: text/html is requested.
    
    Args:
        response_data: FreeTimeResponse data
    
    Returns:
        str: HTML page
    """
    return render_free_time_template(response_data)
