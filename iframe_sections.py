# Iframe section routes for auto-updating components

IFRAME_BASE_STYLE = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root { --gold: #d4af37; --bronze: #cd7f32; --dark-brown: #2c1810; --parchment: #f4e8d0; --accent: #20c997; }
    body { 
        font-family: 'Crimson Text', serif; 
        background: transparent;
        color: var(--parchment); 
        padding: 15px;
    }
    h2, h3, h4 { font-family: 'Cinzel', serif; color: var(--gold); }
    .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; margin: 15px 0; }
    .stat-value { font-size: 1.4em; color: var(--gold); font-family: 'Cinzel', serif; }
    .stat-label { font-size: 0.7em; color: rgba(244, 232, 208, 0.7); text-transform: uppercase; }
    .machine-item { 
        padding: 10px; 
        margin: 8px 0; 
        background: linear-gradient(90deg, rgba(212, 175, 55, 0.12), rgba(205, 127, 50, 0.06)); 
        border-left: 3px solid var(--gold);
        border-radius: 4px;
    }
    .machine-item:hover { background: linear-gradient(90deg, rgba(212, 175, 55, 0.25), rgba(205, 127, 50, 0.15)); }
    .machine-name { font-weight: 700; color: var(--gold); margin-bottom: 5px; }
    .machine-stats { display: flex; justify-content: space-between; font-size: 0.85em; color: rgba(244, 232, 208, 0.9); }
    a { color: var(--gold); text-decoration: none; }
    a:hover { color: #fff; }
    .trend-up { color: #ff6b6b; }
    .trend-down { color: #4dabf7; }
    .trend-stable { color: #ffd43b; }
    .area-code { 
        display: inline-block;
        padding: 3px 8px;
        background: rgba(212, 175, 55, 0.2);
        border-radius: 3px;
        font-family: 'Cinzel', serif;
        font-weight: 700;
    }
</style>
"""
