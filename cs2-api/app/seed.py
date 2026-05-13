from __future__ import annotations

from datetime import datetime, timedelta

from .auth import hash_password

# Map seed data: 9 competitive maps with Chinese names and icons
_MAP_DATA = [
    {"id": 1, "name": "Ancient", "cn": "远古遗迹", "slug": "ancient",
     "overview": "中路控制和甜甜圈争夺是核心，适合多段道具分层推进。",
     "color": "#e6a23c", "file_prefix": "de_ancient"},
    {"id": 2, "name": "Anubis", "cn": "阿努比斯", "slug": "anubis",
     "overview": "中路快攻和A点爆弹是主流打法，水路控制影响B点节奏。",
     "color": "#f56c6c", "file_prefix": "de_anubis"},
    {"id": 3, "name": "Dust II", "cn": "炙热沙城II", "slug": "dust2",
     "overview": "经典长枪图，A门和B洞控制权决定回合走势。",
     "color": "#ff7a18", "file_prefix": "de_dust2"},
    {"id": 4, "name": "Inferno", "cn": "炼狱小镇", "slug": "inferno",
     "overview": "香蕉道节奏和二楼前压应对决定大部分回合走势。",
     "color": "#ffc145", "file_prefix": "de_inferno"},
    {"id": 5, "name": "Mirage", "cn": "荒漠迷城", "slug": "mirage",
     "overview": "中路控制和窗口烟是核心，适合用多段道具把B小和A连接切碎。",
     "color": "#409eff", "file_prefix": "de_mirage"},
    {"id": 6, "name": "Nuke", "cn": "核子危机", "slug": "nuke",
     "overview": "外场切线和黄房协同是T方拉开空间的前提。",
     "color": "#65d6ce", "file_prefix": "de_nuke"},
    {"id": 7, "name": "Overpass", "cn": "死亡游乐园", "slug": "overpass",
     "overview": "工地和长管控制是地图核心，厕所区域适合CT前顶侦查。",
     "color": "#67c23a", "file_prefix": "de_overpass"},
    {"id": 8, "name": "Vertigo", "cn": "殒命大厦", "slug": "vertigo",
     "overview": "A坡和B楼梯分层作战，上下层声音判断至关重要。",
     "color": "#409eff", "file_prefix": "de_vertigo"},
    {"id": 9, "name": "Train", "cn": "列车停放站", "slug": "train",
     "overview": "内外场切换和红楼梯控制是攻防核心，适合慢打试探。",
     "color": "#e6a23c", "file_prefix": "de_train"},
]

# Quick point seed: T/CT staging + A/B sites per map (reduced to keep file manageable)
_POINT_DATA = [
    # id  map  name                key                  x    y   side   type       tags
    # ── Ancient ──
    {"id": 1, "map_id": 1, "name": "T Spawn", "key": "ancient-t", "x": 10, "y": 85, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 2, "map_id": 1, "name": "Donut", "key": "ancient-donut", "x": 50, "y": 50, "side": "BOTH", "point_type": "site", "tags": ["中控"]},
    {"id": 3, "map_id": 1, "name": "A Site", "key": "ancient-a", "x": 78, "y": 35, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    {"id": 4, "map_id": 1, "name": "B Site", "key": "ancient-b", "x": 30, "y": 55, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    # ── Anubis ──
    {"id": 5, "map_id": 2, "name": "T Spawn", "key": "anubis-t", "x": 10, "y": 85, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 6, "map_id": 2, "name": "Mid Bridge", "key": "anubis-mid", "x": 55, "y": 50, "side": "BOTH", "point_type": "site", "tags": ["中路"]},
    {"id": 7, "map_id": 2, "name": "A Site", "key": "anubis-a", "x": 80, "y": 30, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    {"id": 8, "map_id": 2, "name": "B Site", "key": "anubis-b", "x": 25, "y": 55, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    # ── Dust II ──
    {"id": 9, "map_id": 3, "name": "T Spawn", "key": "dust2-t", "x": 10, "y": 85, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 10, "map_id": 3, "name": "A Door", "key": "dust2-adoor", "x": 40, "y": 55, "side": "T", "point_type": "staging", "tags": ["A门"]},
    {"id": 11, "map_id": 3, "name": "Mid Doors", "key": "dust2-mid", "x": 50, "y": 50, "side": "BOTH", "point_type": "aim", "tags": ["中路"]},
    {"id": 12, "map_id": 3, "name": "A Site", "key": "dust2-a", "x": 78, "y": 35, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    {"id": 13, "map_id": 3, "name": "B Site", "key": "dust2-b", "x": 22, "y": 60, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    # ── Inferno ──
    {"id": 14, "map_id": 4, "name": "T Ramp", "key": "inferno-t", "x": 9, "y": 77, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 15, "map_id": 4, "name": "Banana Logs", "key": "inferno-logs", "x": 34, "y": 41, "side": "T", "point_type": "staging", "tags": ["香蕉道"]},
    {"id": 16, "map_id": 4, "name": "CT Coffin", "key": "inferno-coffin", "x": 77, "y": 29, "side": "CT", "point_type": "aim", "tags": ["B点"]},
    {"id": 17, "map_id": 4, "name": "B Site", "key": "inferno-b", "x": 83, "y": 32, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    # ── Mirage ──
    {"id": 18, "map_id": 5, "name": "T Spawn", "key": "mirage-t", "x": 10, "y": 82, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 19, "map_id": 5, "name": "A Ramp", "key": "mirage-ramp", "x": 28, "y": 64, "side": "T", "point_type": "staging", "tags": ["A默认"]},
    {"id": 20, "map_id": 5, "name": "Window", "key": "mirage-window", "x": 47, "y": 37, "side": "CT", "point_type": "aim", "tags": ["中路"]},
    {"id": 21, "map_id": 5, "name": "Connector", "key": "mirage-connector", "x": 58, "y": 49, "side": "CT", "point_type": "utility", "tags": ["中控"]},
    {"id": 22, "map_id": 5, "name": "A Site", "key": "mirage-a", "x": 78, "y": 41, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    # ── Nuke ──
    {"id": 23, "map_id": 6, "name": "T Red Box", "key": "nuke-red", "x": 20, "y": 72, "side": "T", "point_type": "staging", "tags": ["外场"]},
    {"id": 24, "map_id": 6, "name": "Garage Roof", "key": "nuke-garage", "x": 46, "y": 28, "side": "CT", "point_type": "aim", "tags": ["外场"]},
    {"id": 25, "map_id": 6, "name": "Secret", "key": "nuke-secret", "x": 67, "y": 65, "side": "BOTH", "point_type": "utility", "tags": ["地下"]},
    # ── Overpass ──
    {"id": 26, "map_id": 7, "name": "T Spawn", "key": "overpass-t", "x": 10, "y": 85, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 27, "map_id": 7, "name": "Long", "key": "overpass-long", "x": 30, "y": 70, "side": "T", "point_type": "staging", "tags": ["长管"]},
    {"id": 28, "map_id": 7, "name": "Toilets", "key": "overpass-toilets", "x": 55, "y": 50, "side": "BOTH", "point_type": "aim", "tags": ["厕所"]},
    {"id": 29, "map_id": 7, "name": "A Site", "key": "overpass-a", "x": 78, "y": 30, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    {"id": 30, "map_id": 7, "name": "B Site", "key": "overpass-b", "x": 25, "y": 60, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    # ── Vertigo ──
    {"id": 31, "map_id": 8, "name": "T Spawn", "key": "vertigo-t", "x": 10, "y": 85, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 32, "map_id": 8, "name": "A Ramp", "key": "vertigo-aramp", "x": 45, "y": 70, "side": "T", "point_type": "staging", "tags": ["A坡"]},
    {"id": 33, "map_id": 8, "name": "B Stairs", "key": "vertigo-bstairs", "x": 25, "y": 55, "side": "T", "point_type": "staging", "tags": ["B楼梯"]},
    {"id": 34, "map_id": 8, "name": "A Site", "key": "vertigo-a", "x": 75, "y": 30, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    {"id": 35, "map_id": 8, "name": "B Site", "key": "vertigo-b", "x": 25, "y": 35, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    # ── Train ──
    {"id": 36, "map_id": 9, "name": "T Spawn", "key": "train-t", "x": 10, "y": 85, "side": "T", "point_type": "staging", "tags": ["出生点"]},
    {"id": 37, "map_id": 9, "name": "Red Stairs", "key": "train-redstairs", "x": 35, "y": 60, "side": "BOTH", "point_type": "staging", "tags": ["红楼梯"]},
    {"id": 38, "map_id": 9, "name": "A Site", "key": "train-a", "x": 75, "y": 35, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
    {"id": 39, "map_id": 9, "name": "B Site", "key": "train-b", "x": 30, "y": 40, "side": "BOTH", "point_type": "site", "tags": ["爆弹"]},
]


def build_seed_state() -> dict:
    now = datetime.utcnow()

    maps = []
    for m in _MAP_DATA:
        maps.append({
            "id": m["id"],
            "name": f"{m['name']} ({m['cn']})",
            "slug": m["slug"],
            "overview": m["overview"],
            "cover_url": f"/static/assets/maps/icons/{m['file_prefix']}.png",
            "layout_url": f"/static/assets/maps/{m['slug']}-layout.svg",
            "callout_color": m["color"],
            "order": m["id"],
            "status": "published",
            "active_pool": True,
        })

    points = []
    for p in _POINT_DATA:
        points.append({
            "id": p["id"],
            "map_id": p["map_id"],
            "name": p["name"],
            "key": p["key"],
            "x": p["x"],
            "y": p["y"],
            "side": p["side"],
            "point_type": p["point_type"],
            "tags": p["tags"],
        })

    lineups = [
        {
            "id": 1, "map_id": 5, "title": "Mirage 窗口烟", "slug": "mirage-window-smoke",
            "side": "T", "utility_type": "smoke",
            "start_point_id": 18, "aim_point_id": 20, "land_point_id": 20,
            "purpose": "切掉窗口信息，方便中路过点和connector控制。",
            "difficulty": "easy", "summary": "经典中路窗口烟，适合默认开局和中控展开。",
            "steps": ["出生点贴左墙站定", "准星对准屋檐阴影边角", "起跳同时左键投掷"],
            "media": ["/static/assets/maps/mirage-lineup-window.svg"], "status": "published",
        },
        {
            "id": 2, "map_id": 5, "title": "Mirage 连接烟", "slug": "mirage-connector-smoke",
            "side": "T", "utility_type": "smoke",
            "start_point_id": 19, "aim_point_id": 21, "land_point_id": 21,
            "purpose": "切断A连接回防，保护爆弹推进。",
            "difficulty": "medium", "summary": "A坡默认集合后丢的连接烟，适合双烟A爆。",
            "steps": ["A坡左侧木箱靠住", "瞄准连接上方天线", "原地左键投掷"],
            "media": ["/static/assets/maps/mirage-lineup-connector.svg"], "status": "published",
        },
        {
            "id": 3, "map_id": 4, "title": "Inferno 棺材火", "slug": "inferno-coffin-molotov",
            "side": "T", "utility_type": "molotov",
            "start_point_id": 15, "aim_point_id": 16, "land_point_id": 16,
            "purpose": "清理棺材死角，迫使B点CT交位。",
            "difficulty": "easy", "summary": "香蕉道默认道具，适合B爆和二次展开。",
            "steps": ["木头位站定", "准星压在棺材上沿", "跑两步后左键投掷"],
            "media": ["/static/assets/maps/inferno-lineup-coffin.svg"], "status": "published",
        },
        {
            "id": 4, "map_id": 6, "title": "Nuke 外场切线烟", "slug": "nuke-secret-wall-smoke",
            "side": "T", "utility_type": "smoke",
            "start_point_id": 23, "aim_point_id": 24, "land_point_id": 25,
            "purpose": "建立外场烟墙，安全下secret。",
            "difficulty": "hard", "summary": "外场一线烟核心线路，适合标准外场展开。",
            "steps": ["红箱边缘对齐", "对准车库屋顶分界", "跳投完成切线"],
            "media": ["/static/assets/maps/nuke-lineup-secret.svg"], "status": "published",
        },
    ]

    tactics = [
        {
            "id": 1, "map_id": 5, "title": "Mirage A爆双烟闪同步",
            "slug": "mirage-a-exec-double-smoke", "side": "T",
            "goal": "A点爆弹", "phase": "exec", "difficulty": "medium", "players": 4,
            "summary": "窗口烟和连接烟同步落地，配合过点闪一波吃掉A点防守。",
            "note": "如果CT在VIP提前前顶，需要一名中路队员补一颗补位闪。",
            "tags": ["A爆", "双烟", "同步"],
            "cover_url": "/static/assets/maps/icons/de_mirage.png",
            "status": "published", "featured": True,
            "created_at": (now - timedelta(days=2)).isoformat(),
            "routes": [],
            "step_items": [
                {"order": 1, "role": "辅助位", "type": "utility", "instruction": "先给窗口烟，确保中路狙击位失去信息。", "lineup_id": 1},
                {"order": 2, "role": "二道具位", "type": "utility", "instruction": "A坡补连接烟，压缩CT回防路线。", "lineup_id": 2},
                {"order": 3, "role": "主突破", "type": "move", "instruction": "等双烟落地后贴墙出A坡，吃过点闪。", "lineup_id": None},
                {"order": 4, "role": "补枪位", "type": "trade", "instruction": "跟进默认箱和ticket方向补枪。", "lineup_id": None},
            ],
        },
        {
            "id": 2, "map_id": 4, "title": "Inferno B爆棺材火节奏",
            "slug": "inferno-b-hit-coffin-molly", "side": "T",
            "goal": "B点爆弹", "phase": "exec", "difficulty": "easy", "players": 3,
            "summary": "用棺材火把B点守位顶出来，再用人海速度抢包点。",
            "note": "如果CT反清香蕉道失败，保留一颗灭火烟能明显提高容错。",
            "tags": ["B爆", "火攻", "香蕉道"],
            "cover_url": "/static/assets/maps/icons/de_inferno.png",
            "status": "published", "featured": True,
            "created_at": (now - timedelta(days=5)).isoformat(),
            "step_items": [
                {"order": 1, "role": "道具位", "type": "utility", "instruction": "先给棺材火，强制包点内CT转位。", "lineup_id": 3},
                {"order": 2, "role": "主突破", "type": "move", "instruction": "火焰扩散后立刻贴右墙冲B。", "lineup_id": None},
                {"order": 3, "role": "二突破", "type": "hold", "instruction": "优先看三箱和喷泉反打。", "lineup_id": None},
            ],
        },
        {
            "id": 3, "map_id": 6, "title": "Nuke 外场一线烟下secret",
            "slug": "nuke-secret-walkthrough", "side": "T",
            "goal": "外场转地下", "phase": "default", "difficulty": "hard", "players": 4,
            "summary": "靠外场切线拿到地下控制，再衔接B点或回转上层包夹。",
            "note": "如果对手前压黄房，先拿黄房控制再出烟。",
            "tags": ["外场", "地下", "默认"],
            "cover_url": "/static/assets/maps/icons/de_nuke.png",
            "status": "published", "featured": False,
            "created_at": (now - timedelta(days=1)).isoformat(),
            "step_items": [
                {"order": 1, "role": "烟位", "type": "utility", "instruction": "完成外场切线烟，遮蔽主视野。", "lineup_id": 4},
                {"order": 2, "role": "侦查位", "type": "move", "instruction": "贴红箱观察近点，没有近点再下secret。", "lineup_id": None},
                {"order": 3, "role": "补枪位", "type": "trade", "instruction": "第二身位沿烟边补枪，防止CT穿烟前压。", "lineup_id": None},
            ],
        },
    ]

    users = [
        {
            "id": 1, "username": "demo", "email": "demo@cs2tactics.local",
            "password_hash": hash_password("demo123"), "role": "player",
            "favorite_ids": [1], "recent_tactic_ids": [3, 1],
        },
        {
            "id": 2, "username": "admin", "email": "admin@cs2tactics.local",
            "password_hash": hash_password("admin123"), "role": "admin",
            "favorite_ids": [], "recent_tactic_ids": [],
        },
    ]

    return {
        "maps": maps,
        "points": points,
        "lineups": lineups,
        "tactics": tactics,
        "users": users,
        "assets": [],
        "counters": {
            "maps": len(maps) + 1,
            "points": len(points) + 1,
            "lineups": len(lineups) + 1,
            "tactics": len(tactics) + 1,
            "users": len(users) + 1,
            "assets": 1,
        },
    }
