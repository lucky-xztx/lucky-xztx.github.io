# -*- coding: utf-8 -*-
"""
小周博客 · Glass UI 整站重构生成器
从旧 Hexo/Matery 页面中提取内容，用全新毛玻璃模板重新生成全站页面。
保留全部文章与其原始 URL。可重复运行（幂等）。

用法:  python build.py
"""
import os
import re
import json
import zlib
import html as html_mod
import urllib.parse
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))

CACHE_FILE = "_site_data.json"

SITE_NAME = "小周博客"
SITE_DESC = "正青春！"
OWNER = "小周"
FIRST_POST_DATE = date(2022, 10, 15)
GITHUB = "https://github.com/lucky-xztx"

CAT_EMOJI = {
    "Echarts": "📊", "Flink": "🌊", "Flume": "🛢️", "Hadoop": "🐘",
    "Mysql": "🗄️", "Redis": "🍃", "Spark": "⚡", "SQOOP": "🔄",
    "Zookeeper": "🦓",
}

# ============================================================
# 工具
# ============================================================

def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def write(rel_path, content):
    path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("[ OK ]", rel_path)


def esc(s):
    return html_mod.escape(s, quote=True)


def quote_path(p):
    return "/" + urllib.parse.quote(p.strip("/")) + "/"


def strip_tags(fragment):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment)).strip()


def extract_balanced(text, start_marker):
    """从 start_marker 处的 <div ...> 开始，做 div 配平，返回 div 内部 HTML"""
    i = text.find(start_marker)
    if i < 0:
        return None
    open_m = re.compile(r"<div\b", re.I)
    close_m = re.compile(r"</div>", re.I)
    depth = 0
    pos = i
    while pos < len(text):
        no = open_m.search(text, pos)
        nc = close_m.search(text, pos)
        if not nc:
            return None
        if no and no.start() < nc.start():
            depth += 1
            pos = no.end()
        else:
            depth -= 1
            pos = nc.end()
            if depth == 0:
                inner_start = text.index(">", i) + 1
                return text[inner_start:nc.start()]
    return None


# ============================================================
# 内容提取
# ============================================================

def extract_post(rel_html_path):
    """rel_html_path: 形如 2022/11/12/基础折线图/index.html"""
    raw = read(rel_html_path)
    post_url_dir = rel_html_path[: -len("index.html")]  # 2022/11/12/xxx/

    m = re.search(r"<title>(.*?)\s*\|", raw)
    title = html_mod.unescape(m.group(1)) if m else "无标题"

    m = re.search(r"发布日期:&nbsp;&nbsp;\s*([\d-]+)", raw)
    pdate = m.group(1) if m else "2022-01-01"

    cats = []
    for cm in re.finditer(r'href="/categories/([^/"]+)/"', raw):
        c = urllib.parse.unquote(cm.group(1))
        if c not in cats:
            cats.append(c)

    tags = []
    for tm in re.finditer(r'href="/tags/([^/"]+)/"', raw):
        t = urllib.parse.unquote(tm.group(1))
        if t not in tags:
            tags.append(t)

    m = re.search(r"post-cover\"[^>]*style=\"background-image:\s*url\('([^']+)'\)", raw)
    cover = m.group(1) if m else "/medias/featureimages/%d.jpg" % (
        zlib.crc32(title.encode("utf-8")) % 24)

    content = extract_balanced(raw, 'id="articleContent"') or ""

    # 摘要：取正文前几个 <p> 的纯文本
    summary = ""
    for pm in re.finditer(r"<p[^>]*>(.*?)</p>", content, re.S):
        t = strip_tags(pm.group(1))
        if t:
            summary += ("　" if summary else "") + t
        if len(summary) > 110:
            break
    summary = summary[:120] + ("…" if len(summary) > 120 else "")

    # TOC: h1~h3 with id
    toc = []
    for hm in re.finditer(r'<h([123])\s+id="([^"]+)"[^>]*>(.*?)</h\1>', content, re.S):
        level, hid, inner = hm.group(1), hm.group(2), hm.group(3)
        text = strip_tags(inner) or hid
        toc.append({"level": int(level), "id": hid, "text": text})

    words = len(strip_tags(content))

    return {
        "url": quote_path(post_url_dir),
        "title": title,
        "date": pdate,
        "category": cats[0] if cats else "未分类",
        "tags": tags,
        "cover": cover,
        "content": content.strip(),
        "summary": summary,
        "toc": toc,
        "words": words,
    }


def extract_main(rel_html_path):
    """提取旧页面 <main>…</main> 内部（用于关于/友链/联系页）"""
    raw = read(rel_html_path)
    i = raw.find("<main")
    j = raw.find("</main>")
    if i < 0 or j < 0:
        return ""
    inner = raw[i:j]
    k = inner.find(">")
    return inner[k + 1:].strip()


# ============================================================
# 模板
# ============================================================

NAV_ITEMS = [
    ("", "首页", "fa-home"),
    ("tags/", "标签", "fa-tags"),
    ("categories/", "分类", "fa-bookmark"),
    ("archives/", "归档", "fa-archive"),
    ("about/", "关于", "fa-user-circle"),
    ("friends/", "友链", "fa-link"),
]

BASE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="keywords" content="{{SITE_NAME}},博客,大数据,前端">
<meta name="description" content="{{DESC}}">
<title>{{TITLE}} · {{SITE_NAME}}</title>
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="stylesheet" href="/libs/awesome/css/all.min.css">
<link rel="stylesheet" href="/css/glass.css">
<script>document.documentElement.classList.add('js')</script>
</head>
<body>
<div class="bg-stage">
    <div class="aurora-blob b1"></div>
    <div class="aurora-blob b2"></div>
    <div class="aurora-blob b3"></div>
    <div class="aurora-blob b4"></div>
    <div class="noise"></div>
</div>
<div id="cursorGlow"></div>
<div class="read-progress" id="readProgress"></div>

<header class="site-head">
    <nav class="glass-nav">
        <a class="brand" href="/">
            <img src="/medias/logo.png" alt="logo">
            <span class="brand-name">{{SITE_NAME}}</span>
        </a>
        <ul class="nav-links">
            {{NAV_LINKS}}
        </ul>
        <div class="nav-actions">
            <button class="icon-btn js-search" title="搜索 (Ctrl+K)" type="button">
                <i class="fas fa-search"></i>
            </button>
            <button class="icon-btn" id="themeToggle" title="深浅色切换" type="button"
                    onclick="__glassFlipTheme()">
                <i class="fas fa-moon"></i>
            </button>
            <button class="icon-btn nav-burger" title="菜单" type="button">
                <i class="fas fa-bars"></i>
            </button>
        </div>
    </nav>
    <div class="mobile-menu">
        {{MOBILE_LINKS}}
    </div>
</header>

<main>
{{BODY}}
</main>

<footer class="site-foot">
    <div class="foot-social">
        <a href="{{GITHUB}}" target="_blank" rel="noopener" title="GitHub"><i class="fab fa-github"></i></a>
        <a href="mailto:2074553018@qq.com" title="邮件"><i class="fas fa-envelope-open"></i></a>
        <a href="tencent://AddContact/?fromId=50&fromSubId=1&subcmd=all&uin=2074553018" title="QQ"><i class="fab fa-qq"></i></a>
    </div>
    <div class="foot-copy">Copyright © 2022–{{YEAR}} <a href="/about/">{{OWNER}}</a> · {{SITE_DESC}}</div>
    <div class="foot-badge"><i class="fas fa-wand-magic-sparkles"></i> Glass UI 全面重构 · 毛玻璃美学</div>
</footer>

<div id="backTop" class="backtop" title="回到顶部"><i class="fas fa-rocket"></i></div>

<div class="search-mask" id="searchMask">
    <div class="search-panel">
        <div class="search-bar">
            <i class="fas fa-search"></i>
            <input id="searchInput" type="text" placeholder="搜索文章…  (支持标题与正文)" autocomplete="off">
            <kbd>ESC</kbd>
        </div>
        <div class="search-results" id="searchResults">
            <div class="search-hint">输入关键词，实时搜索 ⚡</div>
        </div>
    </div>
</div>

<script src="/libs/jquery/jquery-3.6.0.min.js"></script>
<script src="/libs/lightGallery/js/lightgallery-all.min.js"></script>
<script src="/js/app.js"></script>
</body>
</html>
"""


def render_base(title, desc, body, active=""):
    nav_links = []
    mobile_links = []
    for path, name, icon in NAV_ITEMS:
        href = "/" + path
        cls = ' class="active"' if active == path else ""
        nav_links.append('<li><a href="%s"%s>%s</a></li>' % (href, cls, name))
        mobile_links.append('<a href="%s"%s><i class="fas %s"></i>&nbsp; %s</a>' % (href, cls, icon, name))
    out = (BASE
           .replace("{{TITLE}}", esc(title))
           .replace("{{DESC}}", esc(desc))
           .replace("{{SITE_NAME}}", SITE_NAME)
           .replace("{{OWNER}}", OWNER)
           .replace("{{GITHUB}}", GITHUB)
           .replace("{{YEAR}}", str(date.today().year))
           .replace("{{NAV_LINKS}}", "\n            ".join(nav_links))
           .replace("{{MOBILE_LINKS}}", "\n        ".join(mobile_links))
           .replace("{{BODY}}", body))
    return out


# ---------- 组件 ----------

def card_html(post, extra_cls=""):
    """小红书风格卡片：封面图在上，下方标题 + 作者行"""
    return f"""<a class="note-card reveal {extra_cls}" href="{post['url']}">
    <div class="note-cover">
        <img src="{post['cover']}" alt="{esc(post['title'])}" loading="lazy">
    </div>
    <div class="note-info">
        <h3 class="note-title">{esc(post['title'])}</h3>
        <div class="note-meta">
            <img class="avatar" src="/medias/avatar.jpg" alt="小周">
            <span class="author">{OWNER}</span>
            <span class="note-cat">{CAT_EMOJI.get(post['category'], '✨')} {esc(post['category'])}</span>
        </div>
    </div>
</a>"""


def mini_card_html(post):
    """列表页（标签/分类详情）与首页同款瀑布流卡片"""
    return card_html(post)


def section_head(icon, title, more_href=None, more_text="查看全部 →"):
    more = f'<a class="section-more" href="{more_href}">{more_text}</a>' if more_href else ""
    return f"""<div class="section-head reveal">
    <h2 class="section-title"><i class="{icon}" style="margin-right:10px"></i>{title}</h2>
    {more}
</div>"""


# ============================================================
# 页面生成
# ============================================================

def build_home(posts, all_tags, all_cats, run_days):
    # 小红书式瀑布流：全部文章统一卡片，无 featured 混排
    cards = [card_html(p) for p in posts]

    ticker_items = "".join(
        '<a class="chip" href="/tags/%s/"># %s</a>' % (urllib.parse.quote(t), esc(t))
        for t in all_tags)

    cat_chips = "".join(
        '<a class="chip" href="/categories/%s/">%s %s</a>'
        % (urllib.parse.quote(c), CAT_EMOJI.get(c, "✨"), esc(c))
        for c in all_cats)

    body = f"""
<section class="hero">
    <div class="hero-floats">
        <div class="float-badge f1"><span class="emoji">🐘</span>Hadoop</div>
        <div class="float-badge f2"><span class="emoji">⚡</span>Spark</div>
        <div class="float-badge f3"><span class="emoji">🌊</span>Flink</div>
        <div class="float-badge f4"><span class="emoji">🍃</span>Redis</div>
    </div>
    <div class="hero-badge glass"><span class="dot"></span>正青春 · 知识分享博客</div>
    <h1 class="hero-title">{SITE_NAME}</h1>
    <p class="hero-sub hero-type">“<span id="typer"></span><span class="caret"></span>”</p>
    <div class="hero-cta">
        <a class="btn btn-grad" href="#articles"><i class="fas fa-book-open"></i> 开始阅读</a>
        <a class="btn btn-ghost" href="{GITHUB}" target="_blank" rel="noopener"><i class="fab fa-github"></i> GitHub</a>
    </div>
    <div class="hero-stats glass">
        <div class="stat"><div class="num" data-count="{len(posts)}">0</div><div class="label">文章</div></div>
        <div class="stat"><div class="num" data-count="{len(all_tags)}">0</div><div class="label">标签</div></div>
        <div class="stat"><div class="num" data-count="{len(all_cats)}">0</div><div class="label">分类</div></div>
        <div class="stat"><div class="num" data-count="{run_days}">0</div><div class="label">天陪伴</div></div>
    </div>
    <a class="scroll-hint" href="#articles" title="向下滚动"><i class="fas fa-chevron-down"></i></a>
</section>

<div class="ticker" id="articles">
    <div class="ticker-track">{ticker_items}{ticker_items}</div>
</div>

<section class="section container">
    {section_head('fa-fire', '最新发布')}
    <div class="waterfall">{''.join(cards)}</div>
</section>

<section class="section container">
    {section_head('fa-bookmark', '分类导航', '/categories/', '全部分类 →')}
    <div class="cat-strip glass reveal">{cat_chips}</div>
</section>
"""
    write("index.html", render_base(SITE_NAME, SITE_DESC + " 大数据与前端技术分享", body, active=""))


def build_post_page(post, prev_post, next_post):
    toc_html = ""
    toc_drawer = ""
    if post["toc"]:
        items = []
        for t in post["toc"]:
            cls = "toc-h2" if t["level"] == 2 else ("toc-h3" if t["level"] == 3 else "")
            hid = urllib.parse.quote(t["id"])
            items.append('<li class="%s"><a href="#%s">%s</a></li>' % (cls, hid, esc(t["text"])))
        toc_html = ('<aside class="post-toc glass"><div class="toc-title"><i class="fas fa-list-ul"></i> 目录</div>'
                    '<ol class="toc-list">%s</ol></aside>') % "".join(items)
        # 窄屏：右下角浮动按钮 + 右侧滑出抽屉（目录永远在右边）
        toc_drawer = ("""
<button class="toc-fab" id="tocFab" type="button" title="目录"><i class="fas fa-list-ul"></i></button>
<div class="toc-drawer" id="tocDrawer">
    <div class="toc-drawer-head">
        <span><i class="fas fa-list-ul"></i> 目录</span>
        <button class="toc-drawer-close" id="tocDrawerClose" type="button"><i class="fas fa-xmark"></i></button>
    </div>
    <ol class="toc-list">%s</ol>
</div>
<div class="toc-drawer-mask" id="tocDrawerMask"></div>""") % "".join(items)

    tag_chips = "".join('<a href="/tags/%s/"><span class="chip"># %s</span></a>'
                        % (urllib.parse.quote(t), esc(t)) for t in post["tags"])
    mins = max(1, post["words"] // 400)

    prev_html = next_html = '<div></div>'
    if prev_post:
        prev_html = ('<a class="glass" href="%s"><span class="nav-label"><i class="fas fa-angle-left"></i> 上一篇</span>'
                     '<span class="nav-title">%s</span></a>') % (prev_post["url"], esc(prev_post["title"]))
    if next_post:
        next_html = ('<a class="glass next" href="%s"><span class="nav-label">下一篇 <i class="fas fa-angle-right"></i></span>'
                     '<span class="nav-title">%s</span></a>') % (next_post["url"], esc(next_post["title"]))

    body = f"""
<article>
    <header class="post-head">
        <a class="crumbs" href="/categories/{urllib.parse.quote(post['category'])}/">
            <i class="fas fa-bookmark"></i> {esc(post['category'])}
        </a>
        <h1 class="post-title">{esc(post['title'])}</h1>
        <div class="post-meta">
            <span class="meta-avatar"><img src="/medias/avatar.jpg" alt="小周">{OWNER}</span>
            <span><i class="far fa-calendar"></i>{post['date']}</span>
            <span><i class="far fa-clock"></i>约 {mins} 分钟</span>
        </div>
    </header>

    <div class="post-layout container-wide">
        <div class="post-body glass reveal">
            <div id="articleContent">
{post['content']}
            </div>
            <div class="post-end">
                <div class="end-line"><span>完</span></div>
                <div class="card-tags" style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">
                    {tag_chips}
                </div>
            </div>
        </div>
        {toc_html}
    </div>

    <nav class="post-nav container-wide">
        {prev_html}
        {next_html}
    </nav>
    {toc_drawer}
</article>
"""
    # url 是编码后的链接地址，写文件时要还原成真实目录名
    write(os.path.join(urllib.parse.unquote(post["url"]).strip("/"), "index.html"),
          render_base(post["title"], post["summary"] or SITE_DESC, body))


def build_tags_index(all_tags, tag_count):
    chips = "".join(
        '<a class="chip" href="/tags/%s/" style="--w:%d"># %s <b>%d</b></a>'
        % (urllib.parse.quote(t), tag_count[t], esc(t), tag_count[t])
        for t in sorted(all_tags, key=lambda x: -tag_count[x]))
    body = f"""
<div class="list-hero">
    <span class="lh-icon"><i class="fas fa-tags"></i></span>
    <h1>标签云</h1>
    <p>共 {len(all_tags)} 个标签 · 点击探索</p>
</div>
<section class="section container">
    <div class="cloud-tags glass reveal">{chips}</div>
</section>
"""
    write("tags/index.html", render_base("标签", "全部标签", body, active="tags/"))


def build_tag_detail(tag, posts):
    cards = "".join(mini_card_html(p) for p in posts)
    body = f"""
<div class="list-hero">
    <span class="lh-icon"><i class="fas fa-tag"></i></span>
    <h1># {esc(tag)}</h1>
    <p>共 {len(posts)} 篇文章</p>
</div>
<section class="section container">
    <div class="waterfall">{cards}</div>
</section>
"""
    write(os.path.join("tags", tag, "index.html"),
          render_base("标签: " + tag, "标签 %s 下的文章" % tag, body, active="tags/"))


def build_categories_index(all_cats, cat_count):
    cards = "".join(f"""<a class="cat-card glass reveal" href="/categories/{urllib.parse.quote(c)}/" data-delay="{i % 4 + 1}">
    <span class="cat-emoji">{CAT_EMOJI.get(c, '✨')}</span>
    <span><span class="cat-name">{esc(c)}</span><br><span class="cat-count">{cat_count[c]} 篇文章</span></span>
</a>""" for i, c in enumerate(sorted(all_cats, key=lambda x: -cat_count[x])))
    body = f"""
<div class="list-hero">
    <span class="lh-icon"><i class="fas fa-bookmark"></i></span>
    <h1>分类</h1>
    <p>共 {len(all_cats)} 个分类</p>
</div>
<section class="section container">
    <div class="cat-grid">{cards}</div>
</section>
"""
    write("categories/index.html", render_base("分类", "全部分类", body, active="categories/"))


def build_category_detail(cat, posts):
    cards = "".join(mini_card_html(p) for p in posts)
    body = f"""
<div class="list-hero">
    <span class="lh-icon">{CAT_EMOJI.get(cat, '✨')}</span>
    <h1>{esc(cat)}</h1>
    <p>共 {len(posts)} 篇文章</p>
</div>
<section class="section container">
    <div class="waterfall">{cards}</div>
</section>
"""
    write(os.path.join("categories", cat, "index.html"),
          render_base("分类: " + cat, "分类 %s 下的文章" % cat, body, active="categories/"))


def timeline_html(posts):
    by_month = {}
    for p in posts:
        by_month.setdefault(p["date"][:7], []).append(p)
    parts = []
    for month in sorted(by_month, reverse=True):
        y, m = month.split("-")
        parts.append(f'<div class="tl-year">{y} 年 {int(m)} 月</div>')
        for p in sorted(by_month[month], key=lambda x: x["date"], reverse=True):
            parts.append(f"""<a class="tl-item glass" href="{p['url']}">
    <span class="tl-date">{p['date'][5:]}</span>
    <span class="tl-title">{esc(p['title'])}</span>
</a>""")
    return '<div class="timeline reveal">%s</div>' % "".join(parts)


def build_archives(posts, rel_out, title, active="archives/"):
    body = f"""
<div class="list-hero">
    <span class="lh-icon"><i class="fas fa-archive"></i></span>
    <h1>归档</h1>
    <p>{title} · 共 {len(posts)} 篇</p>
</div>
<section class="section container">
    {timeline_html(posts)}
</section>
"""
    write(os.path.join(rel_out, "index.html"),
          render_base("归档", "文章归档", body, active=active))


def build_about(posts, all_tags, all_cats, run_days):
    """全新关于页：个人名片 + 数据统计 + 技能条 + 技能标签"""
    skills = [("Java", 55), ("JavaScript", 60), ("HTML5", 80),
              ("CSS", 60), ("SQL", 70), ("Python", 75)]
    skill_bars = "".join(f"""<div class="skill">
    <div class="skill-head"><span>{name}</span><span class="skill-num">{val}%</span></div>
    <div class="skill-track"><div class="skill-fill" style="--w:{val}%"></div></div>
</div>""" for name, val in skills)

    chip_cloud = "".join(
        '<a class="chip" href="/tags/%s/"># %s</a>' % (urllib.parse.quote(t), esc(t))
        for t in ["Hadoop", "Linux", "大数据", "Mysql", "Redis", "Spark",
                  "Zookeeper", "Flink", "Flume", "SQOOP", "Echarts", "HTML", "JS"])

    body = f"""
<div class="list-hero">
    <span class="lh-icon"><i class="fas fa-user-astronaut"></i></span>
    <h1>关于我</h1>
    <p>一个爱折腾的学生开发者</p>
</div>

<section class="section container">
    <div class="about-profile glass reveal">
        <div class="about-avatar-ring"><img src="/medias/avatar.jpg" alt="小周"></div>
        <div class="about-name">小周</div>
        <div class="about-career"><i class="fas fa-graduation-cap"></i> Student</div>
        <p class="about-bio">路还在继续，梦还在期许。天高云远，至少看得见。<br>努力与幸运成正比！</p>
        <div class="about-social">
            <a href="{GITHUB}" target="_blank" rel="noopener" title="GitHub"><i class="fab fa-github"></i></a>
            <a href="mailto:2074553018@qq.com" title="邮件联系我"><i class="fas fa-envelope-open"></i></a>
            <a href="tencent://AddContact/?fromId=50&fromSubId=1&subcmd=all&uin=2074553018" title="QQ: 2074553018"><i class="fab fa-qq"></i></a>
        </div>
    </div>

    <div class="about-stats">
        <div class="stat-card glass reveal"><div class="stat"><div class="num" data-count="{len(posts)}">0</div><div class="label">文章</div></div></div>
        <div class="stat-card glass reveal" data-delay="1"><div class="stat"><div class="num" data-count="{len(all_cats)}">0</div><div class="label">分类</div></div></div>
        <div class="stat-card glass reveal" data-delay="2"><div class="stat"><div class="num" data-count="{len(all_tags)}">0</div><div class="label">标签</div></div></div>
        <div class="stat-card glass reveal" data-delay="3"><div class="stat"><div class="num" data-count="{run_days}">0</div><div class="label">天陪伴</div></div></div>
    </div>

    <div class="about-grid">
        <div class="about-panel glass reveal">
            <div class="panel-title"><i class="fas fa-wrench"></i> 我的技能</div>
            {skill_bars}
        </div>
        <div class="about-panel glass reveal" data-delay="1">
            <div class="panel-title"><i class="fas fa-book"></i> 技能标签</div>
            <div class="chip-cloud">{chip_cloud}</div>
            <div class="panel-title" style="margin-top:26px"><i class="fas fa-circle-info"></i> 关于本站</div>
            <div class="about-meta">
                <div class="meta-row"><span>建站时间</span><b>2022 年 10 月</b></div>
                <div class="meta-row"><span>内容来源</span><b>Hexo 文章数据</b></div>
                <div class="meta-row"><span>界面主题</span><b>Glass UI · 毛玻璃设计</b></div>
                <div class="meta-row"><span>座右铭</span><b>正青春！</b></div>
            </div>
        </div>
    </div>
</section>
"""
    write("about/index.html",
          render_base("关于我", "关于小周 - 学生开发者", body, active="about/"))


def build_404():
    body = f"""
<div class="nf-wrap">
    <div class="nf-code">404</div>
    <p><i class="fas fa-ghost"></i> 页面飘走了～去了平行宇宙的某个角落</p>
    <a class="btn btn-grad" href="/"><i class="fas fa-house"></i> 回到首页</a>
</div>
"""
    write("404/index.html", render_base("404", "页面不存在", body))


def build_pagination(posts, page_no, per_page=9):
    total_pages = max(1, -(-len(posts) // per_page))
    chunk = posts[(page_no - 1) * per_page: page_no * per_page]
    if not chunk:
        grid = '<div class="empty-tip glass"><i class="fas fa-mug-hot"></i> 这里没有更多文章了，去<a href="/">首页</a>逛逛吧～</div>'
    else:
        grid = '<div class="waterfall">%s</div>' % "".join(card_html(p) for p in chunk)
    body = f"""
<div class="list-hero">
    <span class="lh-icon"><i class="fas fa-layer-group"></i></span>
    <h1>第 {page_no} 页</h1>
    <p>共 {total_pages} 页 · {len(posts)} 篇文章</p>
</div>
<section class="section container">
    {grid}
    <div style="display:flex;gap:12px;justify-content:center;margin-top:34px">
        {f'<a class="btn btn-ghost" href="/"><i class="fas fa-angle-left"></i> 第 1 页</a>' if page_no > 1 else ''}
        {f'<a class="btn btn-grad" href="/page/{page_no + 1}/">第 {page_no + 1} 页 <i class="fas fa-angle-right"></i></a>' if page_no < total_pages else ''}
    </div>
</section>
"""
    write(os.path.join("page", str(page_no), "index.html"),
          render_base("第 %d 页" % page_no, "文章列表", body))


# ============================================================
# 主流程
# ============================================================

def main():
    # 0. 内容缓存：首次从旧页面提取并落盘；重跑时直接读缓存（旧页面已被新模板覆盖）
    cache_path = os.path.join(ROOT, CACHE_FILE)
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        posts = data["posts"]
        legacy = data["legacy"]
        print("从缓存 %s 读取内容（删除该文件可强制重新提取）" % CACHE_FILE)
    else:
        legacy = {
            "about": extract_main("about/index.html"),
            "friends": extract_main("friends/index.html"),
            "contact": extract_main("contact/index.html"),
        }
        post_files = []
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "2022")):
            if "index.html" in filenames:
                rel = os.path.relpath(os.path.join(dirpath, "index.html"), ROOT)
                post_files.append(rel.replace(os.sep, "/"))
        posts = [extract_post(p) for p in post_files]
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"posts": posts, "legacy": legacy}, f, ensure_ascii=False, indent=1)
    posts.sort(key=lambda x: x["date"], reverse=True)
    print("共 %d 篇文章\n" % len(posts))

    all_tags, tag_count = [], {}
    all_cats, cat_count = [], {}
    for p in posts:
        for t in p["tags"]:
            if t not in all_tags:
                all_tags.append(t)
            tag_count[t] = tag_count.get(t, 0) + 1
        c = p["category"]
        if c not in all_cats:
            all_cats.append(c)
        cat_count[c] = cat_count.get(c, 0) + 1

    run_days = (date.today() - FIRST_POST_DATE).days

    # 2. 首页 / 文章
    build_home(posts, all_tags, all_cats, run_days)
    for i, p in enumerate(posts):
        build_post_page(p, posts[i + 1] if i + 1 < len(posts) else None,
                        posts[i - 1] if i > 0 else None)

    # 3. 标签 / 分类
    build_tags_index(all_tags, tag_count)
    for t in all_tags:
        build_tag_detail(t, [p for p in posts if t in p["tags"]])
    build_categories_index(all_cats, cat_count)
    for c in all_cats:
        build_category_detail(c, [p for p in posts if p["category"] == c])

    # 4. 归档（总览 + 年 + 月 + 旧分页路径）
    build_archives(posts, "archives", "全部文章")
    build_archives([p for p in posts if p["date"].startswith("2022")],
                   os.path.join("archives", "2022"), "2022 年")
    for month in sorted({p["date"][:7] for p in posts}, reverse=True):
        y, m = month.split("-")
        build_archives([p for p in posts if p["date"].startswith(month)],
                       os.path.join("archives", y, m), "%s 年 %s 月" % (y, int(m)))
    build_archives(posts, os.path.join("archives", "page", "2"), "全部文章（第 2 页）")
    build_archives([p for p in posts if p["date"].startswith("2022")],
                   os.path.join("archives", "2022", "page", "2"), "2022 年（第 2 页）")

    # 5. 旧分页页面
    for page_dir in os.listdir(os.path.join(ROOT, "page")):
        if page_dir.isdigit():
            build_pagination(posts, int(page_dir))

    # 6. 关于页（全新模板）/ 友链 / 联系（旧内容 + 新壳，内容来自缓存）
    build_about(posts, all_tags, all_cats, run_days)
    write_legacy = lambda rel_out, title, active, inner: write(
        os.path.join(rel_out, "index.html"),
        render_base(title, title + " - " + SITE_NAME, """
<div class="list-hero">
    <h1 style="margin-top:20px">%s</h1>
</div>
<section class="section container">
    <div class="legacy glass reveal">%s</div>
</section>
""" % (esc(title), inner), active=active))
    write_legacy("friends", "友情链接", "friends/", legacy["friends"])
    write_legacy("contact", "联系我", "", legacy["contact"])

    # 7. 404
    build_404()

    print("\n✨ 全站构建完成！")


if __name__ == "__main__":
    main()
