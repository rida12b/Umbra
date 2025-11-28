"""
Export functionality for Umbra.
Generates stunning interactive HTML dashboards.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import re


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} · Umbra</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/panzoom@9.4.0/dist/panzoom.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-void: #0a0a0c;
            --bg-deep: #0f0f12;
            --bg-surface: rgba(18, 18, 24, 0.8);
            --bg-glass: rgba(255, 255, 255, 0.03);
            --bg-glass-hover: rgba(255, 255, 255, 0.06);
            
            --border-subtle: rgba(255, 255, 255, 0.06);
            --border-medium: rgba(255, 255, 255, 0.1);
            --border-accent: rgba(139, 92, 246, 0.4);
            
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            
            --accent-violet: #8b5cf6;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            
            --gradient-primary: linear-gradient(135deg, var(--accent-violet), var(--accent-blue));
            --gradient-mesh: 
                radial-gradient(at 20% 30%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
                radial-gradient(at 80% 20%, rgba(6, 182, 212, 0.1) 0%, transparent 40%),
                radial-gradient(at 40% 80%, rgba(59, 130, 246, 0.08) 0%, transparent 45%);
            
            --font: 'Outfit', -apple-system, sans-serif;
            --mono: 'JetBrains Mono', monospace;
            
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-xl: 24px;
            
            --shadow-glow: 0 0 60px rgba(139, 92, 246, 0.15);
            --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.3);
            
            --sidebar-width: 340px;
            --chat-height: 280px;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
        }}

        @keyframes pulse-glow {{
            0%, 100% {{ opacity: 0.5; }}
            50% {{ opacity: 1; }}
        }}

        @keyframes gradient-shift {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}

        @keyframes fade-in {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        html, body {{ 
            height: 100%; 
            overflow: hidden;
            background: var(--bg-void);
            color: var(--text-primary);
            font-family: var(--font);
            font-size: 14px;
            -webkit-font-smoothing: antialiased;
        }}

        /* ===== ANIMATED BACKGROUND ===== */
        .bg-mesh {{
            position: fixed;
            inset: 0;
            background: var(--gradient-mesh);
            pointer-events: none;
            z-index: 0;
        }}

        .bg-grid {{
            position: fixed;
            inset: 0;
            background-image: 
                linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }}

        /* ===== LAYOUT ===== */
        .app {{
            display: flex;
            height: 100vh;
            position: relative;
            z-index: 1;
        }}

        /* ===== SIDEBAR ===== */
        .sidebar {{
            width: var(--sidebar-width);
            min-width: 300px;
            max-width: 480px;
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            border-right: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            position: relative;
        }}

        .sidebar-resize {{
            position: absolute;
            right: -3px;
            top: 0;
            width: 6px;
            height: 100%;
            cursor: ew-resize;
            z-index: 50;
            transition: background 0.2s;
        }}
        .sidebar-resize:hover {{ background: var(--accent-violet); }}

        /* Brand */
        .brand {{
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .brand-logo {{
            width: 44px;
            height: 44px;
            background: var(--gradient-primary);
            border-radius: var(--radius-md);
            display: grid;
            place-items: center;
            font-size: 22px;
            box-shadow: var(--shadow-glow);
            animation: float 4s ease-in-out infinite;
        }}

        .brand-text h1 {{
            font-size: 20px;
            font-weight: 700;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .brand-text p {{
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 400;
        }}

        /* Tabs */
        .tabs {{
            display: flex;
            padding: 0.5rem;
            gap: 0.25rem;
            background: var(--bg-glass);
            margin: 1rem;
            border-radius: var(--radius-lg);
        }}

        .tab {{
            flex: 1;
            padding: 0.75rem;
            text-align: center;
            cursor: pointer;
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 500;
            border-radius: var(--radius-md);
            transition: all 0.2s ease;
        }}

        .tab:hover {{ color: var(--text-secondary); background: var(--bg-glass); }}
        .tab.active {{ 
            color: var(--text-primary); 
            background: var(--bg-glass-hover);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}

        /* Panels */
        .panel {{
            flex: 1;
            overflow-y: auto;
            padding: 0 1rem 1rem;
        }}
        .panel.hidden {{ display: none; }}

        .section {{ 
            margin-bottom: 1.5rem;
            animation: fade-in 0.4s ease;
        }}
        
        .section-header {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        /* ===== BENTO GRID ===== */
        .bento {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            margin-bottom: 1rem;
        }}

        .bento-card {{
            background: var(--bg-glass);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 1rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .bento-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--gradient-primary);
            opacity: 0;
            transition: opacity 0.3s;
        }}

        .bento-card:hover {{
            background: var(--bg-glass-hover);
            border-color: var(--border-medium);
            transform: translateY(-2px);
        }}

        .bento-card:hover::before {{ opacity: 1; }}

        .bento-card.large {{
            grid-column: span 2;
        }}

        .bento-value {{
            font-family: var(--mono);
            font-size: 28px;
            font-weight: 700;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .bento-label {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
        }}

        /* Health Card */
        .health-card {{
            background: var(--bg-glass);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-xl);
            padding: 1.25rem;
            display: flex;
            gap: 1rem;
            align-items: center;
            margin-bottom: 1rem;
        }}

        .grade-ring {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            font-size: 28px;
            font-weight: 800;
            position: relative;
        }}

        .grade-ring::before {{
            content: '';
            position: absolute;
            inset: -3px;
            border-radius: 50%;
            padding: 3px;
            background: var(--gradient-primary);
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            -webkit-mask-composite: xor;
            mask-composite: exclude;
        }}

        .grade-ring.A {{ color: var(--accent-emerald); }}
        .grade-ring.B {{ color: #4ade80; }}
        .grade-ring.C {{ color: var(--accent-amber); }}
        .grade-ring.D {{ color: #f97316; }}
        .grade-ring.F {{ color: var(--accent-rose); }}

        .health-info h3 {{ font-size: 15px; font-weight: 600; }}
        .health-info p {{ font-size: 12px; color: var(--text-muted); }}

        /* Chips */
        .chip-wrap {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .chip {{
            background: var(--bg-glass);
            border: 1px solid var(--border-subtle);
            padding: 0.5rem 0.875rem;
            border-radius: var(--radius-lg);
            font-size: 12px;
            font-family: var(--mono);
            color: var(--text-secondary);
            transition: all 0.2s;
            cursor: default;
        }}

        .chip:hover {{
            background: var(--bg-glass-hover);
            border-color: var(--border-medium);
        }}

        .chip.entry {{ 
            border-color: rgba(16, 185, 129, 0.3);
            color: var(--accent-emerald);
        }}
        .chip.api {{ 
            border-color: rgba(59, 130, 246, 0.3);
            color: var(--accent-blue);
        }}

        /* File List */
        .file-list {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .file-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.625rem 0.875rem;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all 0.15s;
            font-family: var(--mono);
            font-size: 12px;
            color: var(--text-secondary);
            background: var(--bg-glass);
            border: 1px solid transparent;
        }}

        .file-row:hover {{
            background: var(--bg-glass-hover);
            border-color: var(--border-subtle);
            color: var(--text-primary);
        }}

        .file-row .lines {{
            color: var(--text-muted);
            font-size: 11px;
        }}

        /* Activity List */
        .activity-list {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .activity-item {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            padding: 0.875rem;
            background: var(--bg-glass);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            animation: fade-in 0.3s ease;
            transition: all 0.2s;
        }}

        .activity-item:hover {{
            background: var(--bg-glass-hover);
            border-color: var(--border-medium);
        }}

        .activity-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .activity-time {{
            font-family: var(--mono);
            font-size: 10px;
            color: var(--text-muted);
            min-width: 55px;
        }}

        .activity-icon {{
            width: 22px;
            height: 22px;
            border-radius: 6px;
            display: grid;
            place-items: center;
            font-size: 11px;
            flex-shrink: 0;
        }}

        .activity-icon.modified {{ background: rgba(59, 130, 246, 0.2); color: var(--accent-blue); }}
        .activity-icon.created {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald); }}
        .activity-icon.deleted {{ background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); }}

        .activity-file {{
            font-family: var(--mono);
            font-size: 12px;
            color: var(--text-primary);
            font-weight: 500;
        }}

        .activity-desc {{
            font-size: 12px;
            color: var(--text-secondary);
            padding-left: 2rem;
            line-height: 1.4;
        }}

        .activity-empty {{
            text-align: center;
            padding: 2rem 1rem;
            color: var(--text-muted);
            font-size: 13px;
        }}

        /* Live indicator */
        .live-indicator {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0.75rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: var(--radius-md);
            font-size: 11px;
            color: var(--accent-emerald);
            margin-bottom: 1rem;
        }}

        .live-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent-emerald);
            animation: pulse-glow 1.5s infinite;
        }}

        /* Issues */
        .issue-card {{
            background: var(--bg-glass);
            border: 1px solid var(--border-subtle);
            border-left: 3px solid var(--accent-amber);
            border-radius: var(--radius-md);
            padding: 0.875rem;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .issue-card:hover {{
            background: var(--bg-glass-hover);
            transform: translateX(4px);
        }}

        .issue-card.critical {{ border-left-color: var(--accent-rose); }}

        .issue-title {{ font-size: 13px; font-weight: 500; margin-bottom: 4px; }}
        .issue-desc {{ font-size: 12px; color: var(--text-muted); line-height: 1.5; }}

        /* Summary */
        .summary-content {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.7;
        }}

        .summary-content h4 {{
            color: var(--text-primary);
            font-size: 14px;
            font-weight: 600;
            margin: 1rem 0 0.5rem;
        }}

        .summary-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0.75rem 0;
            font-size: 12px;
        }}

        .summary-content th,
        .summary-content td {{
            padding: 0.625rem;
            text-align: left;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .summary-content th {{
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.5px;
        }}

        .summary-content code {{
            background: var(--bg-glass);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: var(--mono);
            font-size: 11px;
        }}

        /* ===== MAIN AREA ===== */
        .main {{
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
            position: relative;
        }}

        .diagram-area {{
            flex: 1;
            position: relative;
            overflow: hidden;
        }}

        .diagram-toolbar {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            display: flex;
            gap: 0.5rem;
            z-index: 100;
        }}

        .tool-btn {{
            width: 40px;
            height: 40px;
            background: var(--bg-surface);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            display: grid;
            place-items: center;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s;
        }}

        .tool-btn:hover {{
            background: var(--bg-glass-hover);
            border-color: var(--border-medium);
            transform: scale(1.05);
        }}

        .tool-btn:active {{ transform: scale(0.95); }}

        #diagram-wrapper {{
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}

        #diagram-content {{
            display: inline-block;
            padding: 3rem;
            min-width: 100%;
            min-height: 100%;
        }}

        .mermaid {{
            display: flex;
            justify-content: center;
        }}

        /* ===== CHAT PANEL ===== */
        .chat-panel {{
            height: var(--chat-height);
            min-height: 200px;
            max-height: 50vh;
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            border-top: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            position: relative;
        }}

        .chat-resize {{
            position: absolute;
            top: -4px;
            left: 0;
            width: 100%;
            height: 8px;
            cursor: ns-resize;
            z-index: 50;
        }}
        .chat-resize:hover {{ background: linear-gradient(to bottom, var(--accent-violet), transparent); }}

        .chat-header {{
            padding: 0.875rem 1.25rem;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-glass);
        }}

        .chat-title {{
            font-weight: 600;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 0.625rem;
        }}

        .chat-title span {{ font-size: 18px; }}

        .status {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-muted);
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--text-muted);
            transition: all 0.3s;
        }}

        .status-dot.online {{ 
            background: var(--accent-emerald); 
            box-shadow: 0 0 12px var(--accent-emerald);
            animation: pulse-glow 2s infinite;
        }}

        .chat-body {{
            flex: 1;
            overflow-y: auto;
            padding: 1rem 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .msg {{
            display: flex;
            gap: 0.75rem;
            max-width: 85%;
            animation: fade-in 0.3s ease;
        }}
        
        .msg.user {{ flex-direction: row-reverse; align-self: flex-end; }}

        .msg-avatar {{
            width: 32px;
            height: 32px;
            border-radius: var(--radius-md);
            display: grid;
            place-items: center;
            font-size: 14px;
            font-weight: 600;
            flex-shrink: 0;
        }}

        .msg-avatar.ai {{ background: var(--gradient-primary); }}
        .msg-avatar.user {{ background: var(--bg-glass); color: var(--text-muted); }}

        .msg-bubble {{
            background: var(--bg-glass);
            border: 1px solid var(--border-subtle);
            padding: 0.875rem 1rem;
            border-radius: var(--radius-lg);
            font-size: 13px;
            line-height: 1.6;
        }}

        .msg.user .msg-bubble {{
            background: var(--gradient-primary);
            border: none;
        }}

        .msg-bubble code {{
            font-family: var(--mono);
            background: rgba(0,0,0,0.3);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }}

        .msg-bubble pre {{
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border-subtle);
            padding: 0.75rem;
            border-radius: var(--radius-md);
            overflow-x: auto;
            margin: 0.5rem 0;
        }}

        .chat-input-wrap {{
            padding: 0.875rem 1.25rem;
            border-top: 1px solid var(--border-subtle);
            display: flex;
            gap: 0.625rem;
            background: var(--bg-glass);
        }}

        .chat-input {{
            flex: 1;
            background: var(--bg-void);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 0.875rem 1rem;
            color: var(--text-primary);
            font-family: var(--font);
            font-size: 13px;
            outline: none;
            transition: all 0.2s;
        }}

        .chat-input:focus {{ 
            border-color: var(--accent-violet); 
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
        }}
        .chat-input::placeholder {{ color: var(--text-muted); }}

        .send-btn {{
            background: var(--gradient-primary);
            color: white;
            border: none;
            border-radius: var(--radius-lg);
            padding: 0 1.5rem;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .send-btn:hover {{ filter: brightness(1.1); transform: scale(1.02); }}
        .send-btn:active {{ transform: scale(0.98); }}
        .send-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}

        /* ===== COMMAND PALETTE (Ctrl+K) ===== */
        .cmd-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: none;
            place-items: center;
        }}

        .cmd-overlay.open {{ display: grid; }}

        .cmd-modal {{
            width: 560px;
            max-width: 90vw;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-xl);
            overflow: hidden;
            box-shadow: var(--shadow-card), var(--shadow-glow);
            animation: fade-in 0.2s ease;
        }}

        .cmd-input-wrap {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .cmd-icon {{ font-size: 20px; color: var(--text-muted); }}

        .cmd-input {{
            flex: 1;
            background: none;
            border: none;
            outline: none;
            font-size: 16px;
            color: var(--text-primary);
            font-family: var(--font);
        }}

        .cmd-input::placeholder {{ color: var(--text-muted); }}

        .cmd-hint {{
            font-size: 12px;
            color: var(--text-muted);
            padding: 4px 8px;
            background: var(--bg-glass);
            border-radius: 4px;
        }}

        .cmd-results {{
            max-height: 320px;
            overflow-y: auto;
            padding: 0.5rem;
        }}

        .cmd-item {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: background 0.15s;
        }}

        .cmd-item:hover, .cmd-item.selected {{ background: var(--bg-glass-hover); }}

        .cmd-item-icon {{
            width: 28px;
            height: 28px;
            background: var(--bg-glass);
            border-radius: 6px;
            display: grid;
            place-items: center;
            font-size: 14px;
        }}

        .cmd-item-text {{ flex: 1; }}
        .cmd-item-title {{ font-size: 14px; font-weight: 500; }}
        .cmd-item-path {{ font-size: 11px; color: var(--text-muted); font-family: var(--mono); }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: var(--border-subtle); border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: var(--border-medium); }}
    </style>
</head>
<body>
    <!-- Animated Background -->
    <div class="bg-mesh"></div>
    <div class="bg-grid"></div>

    <div class="app">
        <!-- SIDEBAR -->
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-resize" id="sidebar-resize"></div>
            
            <div class="brand">
                <div class="brand-logo">🌑</div>
                <div class="brand-text">
                    <h1>Umbra</h1>
                    <p>{project_name}</p>
                </div>
            </div>

            <div class="tabs">
                <div class="tab active" data-tab="overview">Overview</div>
                <div class="tab" data-tab="activity">Activity</div>
                <div class="tab" data-tab="files">Files</div>
            </div>

            <!-- Overview Panel -->
            <div class="panel" id="panel-overview">
                <div class="section">
                    <div class="health-card">
                        <div class="grade-ring {health_grade}">{health_grade}</div>
                        <div class="health-info">
                            <h3>Architecture Health</h3>
                            <p>{health_score}/100 · {health_status}</p>
                        </div>
                    </div>
                    
                    <div class="bento">
                        <div class="bento-card">
                            <div class="bento-value">{total_files}</div>
                            <div class="bento-label">Files</div>
                        </div>
                        <div class="bento-card">
                            <div class="bento-value">{total_lines}</div>
                            <div class="bento-label">Lines of Code</div>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-header">🚀 Entry Points</div>
                    <div class="chip-wrap">{entry_points_html}</div>
                </div>

                <div class="section">
                    <div class="section-header">🌐 External Services</div>
                    <div class="chip-wrap">{external_apis_html}</div>
                </div>

                <div class="section">
                    <div class="section-header">📋 Summary</div>
                    <div class="summary-content">{summary_html}</div>
                </div>
            </div>

            <!-- Activity Panel -->
            <div class="panel hidden" id="panel-activity">
                <div class="section">
                    <div class="section-header">🔄 Recent Changes</div>
                    <div class="activity-list">{recent_changes_html}</div>
                </div>
                
                <div class="section">
                    <div class="section-header">⚠️ Issues ({total_issues})</div>
                    {issues_html}
                </div>
            </div>

            <!-- Files Panel -->
            <div class="panel hidden" id="panel-files">
                <div class="section">
                    <div class="section-header">📁 All Files ({total_files})</div>
                    <div class="file-list">{files_html}</div>
                </div>
            </div>
        </aside>

        <!-- MAIN AREA -->
        <main class="main">
            <div class="diagram-area">
                <div class="diagram-toolbar">
                    <button class="tool-btn" onclick="zoomIn()" title="Zoom In (+ key)">+</button>
                    <button class="tool-btn" onclick="zoomOut()" title="Zoom Out (- key)">−</button>
                    <button class="tool-btn" onclick="resetZoom()" title="Reset (0 key)">↺</button>
                    <button class="tool-btn" onclick="exportSVG()" title="Export SVG">📥</button>
                </div>
                <div id="diagram-wrapper">
                    <div id="diagram-content">
                        <pre class="mermaid">{mermaid_diagram}</pre>
                    </div>
                </div>
            </div>

            <!-- CHAT PANEL -->
            <div class="chat-panel" id="chat-panel">
                <div class="chat-resize" id="chat-resize"></div>
                
                <div class="chat-header">
                    <div class="chat-title">
                        <span>💬</span> Ask Umbra
                    </div>
                    <div class="status">
                        <span class="status-dot" id="status-dot"></span>
                        <span id="status-text">Connecting...</span>
                    </div>
                </div>

                <div class="chat-body" id="chat-body">
                    <div class="msg">
                        <div class="msg-avatar ai">U</div>
                        <div class="msg-bubble">
                            Hey! I've analyzed <strong>{project_name}</strong>. Ask me anything about the architecture, code flow, or specific files.
                        </div>
                    </div>
                </div>

                <div class="chat-input-wrap">
                    <input type="text" id="chat-input" class="chat-input" 
                           placeholder="Ask about this codebase... (/ to focus)" 
                           onkeydown="if(event.key==='Enter') sendMsg()">
                    <button id="send-btn" class="send-btn" onclick="sendMsg()">Send</button>
                </div>
            </div>
        </main>
    </div>

    <!-- Command Palette (Ctrl+K) -->
    <div class="cmd-overlay" id="cmd-overlay" onclick="if(event.target===this) closeCmd()">
        <div class="cmd-modal">
            <div class="cmd-input-wrap">
                <span class="cmd-icon">🔍</span>
                <input type="text" class="cmd-input" id="cmd-input" 
                       placeholder="Search files, functions..." 
                       oninput="searchFiles(this.value)">
                <span class="cmd-hint">ESC</span>
            </div>
            <div class="cmd-results" id="cmd-results"></div>
        </div>
    </div>

    <script>
        // ===== FILE INDEX =====
        const fileIndex = {files_json};

        // ===== MERMAID =====
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'base',
            themeVariables: {{
                darkMode: true,
                background: '#0a0a0c',
                primaryColor: '#8b5cf6',
                primaryTextColor: '#f8fafc',
                primaryBorderColor: 'rgba(255,255,255,0.1)',
                lineColor: '#8b5cf6',
                secondaryColor: '#12121a',
                tertiaryColor: '#0f0f12',
                mainBkg: '#12121a',
                nodeBorder: '#8b5cf6',
                clusterBkg: '#0f0f12',
                clusterBorder: 'rgba(255,255,255,0.1)',
                titleColor: '#f8fafc',
                edgeLabelBackground: '#12121a',
                nodeTextColor: '#f8fafc'
            }},
            flowchart: {{ curve: 'basis', padding: 25, htmlLabels: true }}
        }});

        // ===== PANZOOM =====
        let pz = null;
        
        function initPanzoom() {{
            const el = document.getElementById('diagram-content');
            if (el && typeof panzoom !== 'undefined') {{
                pz = panzoom(el, {{
                    maxZoom: 5,
                    minZoom: 0.15,
                    initialZoom: 0.85,
                    bounds: false
                }});
            }}
        }}

        function zoomIn() {{ if(pz) pz.smoothZoom(0, 0, 1.4); }}
        function zoomOut() {{ if(pz) pz.smoothZoom(0, 0, 0.7); }}
        function resetZoom() {{ if(pz) {{ pz.moveTo(0, 0); pz.zoomAbs(0, 0, 0.85); }} }}

        // ===== EXPORT SVG =====
        function exportSVG() {{
            const svg = document.querySelector('.mermaid svg');
            if (!svg) return alert('No diagram to export');
            const data = new XMLSerializer().serializeToString(svg);
            const blob = new Blob([data], {{ type: 'image/svg+xml' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{project_name}-architecture.svg';
            a.click();
            URL.revokeObjectURL(url);
        }}

        // ===== TABS =====
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
                tab.classList.add('active');
                document.getElementById('panel-' + tab.dataset.tab).classList.remove('hidden');
            }});
        }});

        // ===== RESIZE =====
        function setupResize(handleId, targetId, dim, min, max) {{
            const h = document.getElementById(handleId);
            const t = document.getElementById(targetId);
            let startPos, startSize;
            h.addEventListener('mousedown', e => {{
                startPos = dim === 'width' ? e.clientX : e.clientY;
                startSize = dim === 'width' ? t.offsetWidth : t.offsetHeight;
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
                document.body.style.cursor = dim === 'width' ? 'ew-resize' : 'ns-resize';
                document.body.style.userSelect = 'none';
            }});
            function onMove(e) {{
                const cur = dim === 'width' ? e.clientX : e.clientY;
                let size = dim === 'width' ? startSize + (cur - startPos) : startSize - (cur - startPos);
                size = Math.max(min, Math.min(max, size));
                t.style[dim] = size + 'px';
            }}
            function onUp() {{
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }}
        }}

        // ===== COMMAND PALETTE =====
        function openCmd() {{ document.getElementById('cmd-overlay').classList.add('open'); document.getElementById('cmd-input').focus(); }}
        function closeCmd() {{ document.getElementById('cmd-overlay').classList.remove('open'); document.getElementById('cmd-input').value = ''; }}
        
        function searchFiles(q) {{
            const res = document.getElementById('cmd-results');
            if (!q) {{ res.innerHTML = ''; return; }}
            const matches = fileIndex.filter(f => f.path.toLowerCase().includes(q.toLowerCase())).slice(0, 10);
            res.innerHTML = matches.map(f => `
                <div class="cmd-item" onclick="closeCmd()">
                    <div class="cmd-item-icon">📄</div>
                    <div class="cmd-item-text">
                        <div class="cmd-item-title">${{f.path.split('/').pop()}}</div>
                        <div class="cmd-item-path">${{f.path}}</div>
                    </div>
                </div>
            `).join('') || '<div style="padding:1rem;color:var(--text-muted);">No results</div>';
        }}

        // ===== KEYBOARD SHORTCUTS =====
        document.addEventListener('keydown', e => {{
            if (e.key === 'Escape') closeCmd();
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{ e.preventDefault(); openCmd(); }}
            if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {{ e.preventDefault(); document.getElementById('chat-input').focus(); }}
            if (e.key === '+' || e.key === '=') zoomIn();
            if (e.key === '-') zoomOut();
            if (e.key === '0') resetZoom();
        }});

        // ===== CHAT =====
        const SERVER = 'http://localhost:8765';
        let isConnected = false;

        async function checkServer() {{
            const dot = document.getElementById('status-dot');
            const txt = document.getElementById('status-text');
            try {{
                const res = await fetch(SERVER + '/health');
                if (res.ok) {{ dot.classList.add('online'); txt.textContent = 'Connected'; isConnected = true; }}
            }} catch {{ dot.classList.remove('online'); txt.textContent = 'Run: umbra serve'; isConnected = false; }}
        }}

        async function sendMsg() {{
            const input = document.getElementById('chat-input');
            const btn = document.getElementById('send-btn');
            const q = input.value.trim();
            if (!q) return;
            if (!isConnected) {{ addBubble('ai', '⚠️ Server offline. Run <code>umbra serve .</code>'); return; }}
            addBubble('user', q);
            input.value = '';
            btn.disabled = true;
            try {{
                const res = await fetch(SERVER + '/chat', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{question: q}}) }});
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                addBubble('ai', formatMd(data.answer));
            }} catch (e) {{ addBubble('ai', '⚠️ ' + e.message); }}
            btn.disabled = false;
            input.focus();
        }}

        function addBubble(role, html) {{
            const c = document.getElementById('chat-body');
            const d = document.createElement('div');
            d.className = 'msg ' + role;
            d.innerHTML = `<div class="msg-avatar ${{role}}">${{role === 'ai' ? 'U' : 'Y'}}</div><div class="msg-bubble">${{html}}</div>`;
            c.appendChild(d);
            c.scrollTop = c.scrollHeight;
        }}

        function formatMd(t) {{
            return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
                .replace(/```([\\s\\S]*?)```/g,'<pre><code>$1</code></pre>')
                .replace(/`([^`]+)`/g,'<code>$1</code>')
                .replace(/\\*\\*([^*]+)\\*\\*/g,'<strong>$1</strong>')
                .replace(/\\n/g,'<br>');
        }}

        // ===== AUTO-REFRESH =====
        let lastModified = '{last_modified}';
        
        async function checkForUpdates() {{
            try {{
                // Reload the page if file was updated
                const res = await fetch(window.location.href, {{ method: 'HEAD' }});
                const modified = res.headers.get('Last-Modified');
                if (modified && modified !== lastModified) {{
                    window.location.reload();
                }}
            }} catch (e) {{
                // Ignore errors
            }}
        }}

        // ===== INIT =====
        window.addEventListener('DOMContentLoaded', () => {{
            setTimeout(initPanzoom, 500);
            setupResize('sidebar-resize', 'sidebar', 'width', 300, 500);
            setupResize('chat-resize', 'chat-panel', 'height', 200, window.innerHeight * 0.5);
            checkServer();
            setInterval(checkServer, 5000);
            
            // Check for updates every 3 seconds
            setInterval(checkForUpdates, 3000);
        }});
    </script>
</body>
</html>
'''


def markdown_to_html(md: str) -> str:
    """Convert markdown to beautiful HTML with table support."""
    if not md:
        return "No summary available."
    
    html = md
    
    # Parse tables
    table_pattern = r'\|(.+)\|\n\|[-:| ]+\|\n((?:\|.+\|\n?)+)'
    
    def table_to_html(match):
        header_row = match.group(1)
        body_rows = match.group(2).strip().split('\n')
        
        headers = [h.strip() for h in header_row.split('|') if h.strip()]
        
        result = '<table>'
        result += '<thead><tr>'
        for h in headers:
            result += f'<th>{h}</th>'
        result += '</tr></thead><tbody>'
        
        for row in body_rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            result += '<tr>'
            for c in cells:
                result += f'<td>{c}</td>'
            result += '</tr>'
        
        result += '</tbody></table>'
        return result
    
    html = re.sub(table_pattern, table_to_html, html)
    
    # Headers
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    
    # Bold & code
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Lists
    html = re.sub(r'^\s*[-*] (.+)$', r'<div style="margin-left:1rem;">• \1</div>', html, flags=re.MULTILINE)
    
    # Line breaks
    html = html.replace('\n\n', '<br><br>')
    
    return html


def extract_entry_points(mermaid: str) -> list:
    """Extract entry point files from diagram."""
    entries = []
    keywords = ['main.py', 'app.py', 'index.ts', 'index.js', 'server.py', '__main__.py']
    for kw in keywords:
        if kw in mermaid.lower() or kw.replace('.py', '[') in mermaid.lower():
            entries.append(kw)
    return entries if entries else ['main.py']


def extract_external_apis(mermaid: str) -> list:
    """Extract external APIs from diagram."""
    apis = []
    keywords = ['Gemini', 'OpenAI', 'GPT', 'Claude', 'Stripe', 'Firebase', 'Supabase', 
                'PostgreSQL', 'MongoDB', 'Redis', 'AWS', 'Azure', 'GCP', 'Twilio', 'SendGrid']
    for kw in keywords:
        if kw.lower() in mermaid.lower():
            apis.append(kw)
    return apis if apis else ['None detected']


def generate_files_html(files: list) -> str:
    """Generate HTML for file list."""
    if not files:
        return '<div class="file-row"><span style="color:var(--text-muted);">No files analyzed</span></div>'
    
    html = ""
    for path, lines in files:
        html += f'<div class="file-row"><span>{path}</span><span class="lines">{lines} lines</span></div>'
    return html


def generate_issues_html(insights: list) -> str:
    """Generate HTML for issues."""
    if not insights:
        return '<div style="color:var(--text-muted);font-size:13px;padding:1rem;text-align:center;">✨ No issues found. Nice!</div>'
    
    html = ""
    for i in insights:
        sev = "critical" if "critical" in str(getattr(i, 'severity', '')).lower() else ""
        html += f'''
        <div class="issue-card {sev}">
            <div class="issue-title">{i.title}</div>
            <div class="issue-desc">{i.recommendation}</div>
        </div>
        '''
    return html


def generate_recent_changes_html(changes: list) -> str:
    """Generate HTML for recent changes with AI descriptions."""
    if not changes:
        return '''
        <div class="activity-empty">
            <div>🎯 Watching for changes...</div>
            <div style="margin-top:0.5rem;font-size:11px;">Edit a file to see activity here</div>
        </div>
        '''
    
    html = '''
    <div class="live-indicator">
        <div class="live-dot"></div>
        <span>Live updates enabled</span>
    </div>
    '''
    
    for change in changes[:10]:
        time_str = change.get('time', '')
        file_name = change.get('file', 'unknown')
        change_type = change.get('type', 'modified')
        description = change.get('description', '')
        
        icon_class = 'modified'
        icon = '✏️'
        if change_type == 'created':
            icon_class = 'created'
            icon = '➕'
        elif change_type == 'deleted':
            icon_class = 'deleted'
            icon = '🗑️'
        
        # Build description HTML
        desc_html = f'<div class="activity-desc">{description}</div>' if description else ''
        
        html += f'''
        <div class="activity-item">
            <div class="activity-header">
                <div class="activity-time">{time_str}</div>
                <div class="activity-icon {icon_class}">{icon}</div>
                <div class="activity-file">{file_name}</div>
            </div>
            {desc_html}
        </div>
        '''
    
    return html


def export_html(
    input_file: str,
    output_file: str,
    project_name: str | None = None,
    analysis: Dict[str, Any] | None = None,
) -> None:
    """Export architecture to stunning dashboard."""
    import json
    
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    content = input_path.read_text(encoding="utf-8")
    
    # Extract Mermaid
    mermaid = ""
    if "```mermaid" in content:
        start = content.index("```mermaid") + len("```mermaid")
        end = content.index("```", start)
        mermaid = content[start:end].strip()
    
    # Extract Summary
    summary = ""
    if "## Project Summary" in content:
        start = content.index("## Project Summary") + len("## Project Summary")
        end = content.index("## System Overview") if "## System Overview" in content else len(content)
        summary = content[start:end].strip()

    # Default analysis
    if analysis is None:
        analysis = {
            'metrics': {'total_files': 0, 'total_lines': 0, 'largest_files': []},
            'insights': [],
            'health': {'score': 0, 'grade': '?', 'status': 'Unknown'},
            'recent_changes': []
        }
    
    metrics = analysis.get('metrics', {})
    health = analysis.get('health', {})
    insights = analysis.get('insights', [])
    largest_files = metrics.get('largest_files', [])
    recent_changes = analysis.get('recent_changes', [])
    
    # Prepare file index for search
    file_index = [{"path": f[0], "lines": f[1]} for f in largest_files]
    
    # Generate chips
    entry_points = extract_entry_points(mermaid)
    external_apis = extract_external_apis(mermaid)
    
    entry_html = ''.join([f'<span class="chip entry">{e}</span>' for e in entry_points])
    api_html = ''.join([f'<span class="chip api">{a}</span>' for a in external_apis])
    
    # Generate timestamp for auto-refresh
    last_modified = datetime.now().isoformat()
    
    html = HTML_TEMPLATE.format(
        project_name=project_name or "Project",
        mermaid_diagram=mermaid,
        health_score=health.get('score', 0),
        health_grade=health.get('grade', 'C'),
        health_status=health.get('status', 'Unknown'),
        total_files=metrics.get('total_files', 0),
        total_lines=metrics.get('total_lines', 0),
        total_issues=len(insights),
        entry_points_html=entry_html,
        external_apis_html=api_html,
        summary_html=markdown_to_html(summary),
        files_html=generate_files_html(largest_files),
        issues_html=generate_issues_html(insights),
        recent_changes_html=generate_recent_changes_html(recent_changes),
        files_json=json.dumps(file_index),
        last_modified=last_modified
    )
    
    Path(output_file).write_text(html, encoding="utf-8")
