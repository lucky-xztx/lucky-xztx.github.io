/* ==========================================================================
   小周博客 · Glass UI — 交互脚本
   主题切换 / 打字机 / 计数动画 / 滚动浮现 / 卡片倾斜 / 光标光晕
   搜索 / 阅读进度 / TOC 同步 / 代码块增强 / 图片灯箱 / 返回顶部
   ========================================================================== */
(function () {
    'use strict';

    var d = document;
    var $ = function (s, c) { return (c || d).querySelector(s); };
    var $$ = function (s, c) { return Array.prototype.slice.call((c || d).querySelectorAll(s)); };
    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var desktop = window.innerWidth > 768;

    /* ================= 1. 主题（自动 / 手动记忆） ================= */
    (function theme() {
        var saved = null;
        try { saved = localStorage.getItem('glass-theme'); } catch (e) { /* ignore */ }
        // 兼容旧主题的偏好
        if (!saved) {
            try {
                saved = localStorage.getItem('isDark') === '1' ? 'dark'
                      : localStorage.getItem('isDark') === '0' ? 'light' : null;
            } catch (e) { /* ignore */ }
        }
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        apply(saved || (prefersDark ? 'dark' : 'light'));

        function apply(mode) {
            d.body.classList.toggle('dark', mode === 'dark');
            var icon = $('#themeToggle i');
            if (icon) icon.className = mode === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }

        window.__glassFlipTheme = function () {
            var dark = d.body.classList.toggle('dark');
            try {
                localStorage.setItem('glass-theme', dark ? 'dark' : 'light');
                localStorage.setItem('isDark', dark ? '1' : '0'); // 旧字段同步
            } catch (e) { /* ignore */ }
            var icon = $('#themeToggle i');
            if (icon) icon.className = dark ? 'fas fa-sun' : 'fas fa-moon';
        };
    })();

    /* ================= 2. 导航：滚动收缩 / 移动端抽屉 ================= */
    (function navbar() {
        var head = $('.site-head');
        var burger = $('.nav-burger');
        var menu = $('.mobile-menu');

        function onScroll() {
            if (head) head.classList.toggle('is-scrolled', window.scrollY > 24);
        }
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();

        if (burger && menu) {
            burger.addEventListener('click', function () {
                menu.classList.toggle('open');
                var icon = burger.querySelector('i');
                if (icon) icon.className = menu.classList.contains('open') ? 'fas fa-xmark' : 'fas fa-bars';
            });
            $$('a', menu).forEach(function (a) {
                a.addEventListener('click', function () { menu.classList.remove('open'); });
            });
            d.addEventListener('click', function (e) {
                if (!menu.contains(e.target) && !burger.contains(e.target)) menu.classList.remove('open');
            });
        }
    })();

    /* ================= 3. 首页打字机 ================= */
    (function typer() {
        var el = $('#typer');
        if (!el || reduced) {
            if (el) el.textContent = '从来没有真正的绝境，只有心灵的迷途';
            return;
        }
        var lines = [
            '从来没有真正的绝境，只有心灵的迷途',
            'Never really desperate, only the lost of the soul',
            '努力与幸运成正比 ✨',
            '大数据 · 前端 · 每一篇都是一次冒险 🚀'
        ];
        var li = 0, ci = 0, deleting = false;
        (function tick() {
            var text = lines[li];
            el.textContent = text.slice(0, ci);
            var delay = deleting ? 34 : 92;
            if (!deleting && ci === text.length) { delay = 2200; deleting = true; }
            else if (deleting && ci === 0) { deleting = false; li = (li + 1) % lines.length; delay = 420; }
            else ci += deleting ? -1 : 1;
            setTimeout(tick, delay);
        })();
    })();

    /* ================= 4. 数字滚动动画 ================= */
    (function counters() {
        var nums = $$('.stat .num[data-count]');
        if (!nums.length || reduced || !('IntersectionObserver' in window)) {
            nums.forEach(function (n) { n.textContent = n.getAttribute('data-count'); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
                if (!en.isIntersecting) return;
                io.unobserve(en.target);
                runCount(en.target);
            });
        }, { threshold: .4 });
        nums.forEach(function (n) { io.observe(n); });
        // 兜底：IO 未触发时按几何位置补跑
        function fallback() {
            nums.forEach(function (n) {
                if (n.textContent === '0' && n.getBoundingClientRect().top < innerHeight) runCount(n);
            });
        }
        setTimeout(fallback, 1200);
        window.addEventListener('scroll', function () {
            requestAnimationFrame(fallback);
        }, { passive: true });

        function runCount(el) {
            if (el.dataset.done) return;
            el.dataset.done = '1';
            var target = parseInt(el.getAttribute('data-count'), 10) || 0;
            var t0 = null;
            (function step(ts) {
                if (!t0) t0 = ts;
                var p = Math.min((ts - t0) / 1200, 1);
                el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
                if (p < 1) requestAnimationFrame(step);
            })(performance.now());
        }
    })();

    /* ================= 5. 滚动浮现 ================= */
    (function reveal() {
        var items = $$('.reveal');
        if (!items.length) return;
        if (reduced || !('IntersectionObserver' in window)) {
            items.forEach(function (it) { it.classList.add('in'); });
            return;
        }
        var pending = items.slice();
        function release(el) {
            el.classList.add('in');
            var i = pending.indexOf(el);
            if (i > -1) pending.splice(i, 1);
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
                if (en.isIntersecting) { release(en.target); io.unobserve(en.target); }
            });
        }, { threshold: .12, rootMargin: '0px 0px -6% 0px' });
        items.forEach(function (it) { io.observe(it); });

        // 兜底：个别环境下 IO 回调不触发时，用几何计算保证内容可见
        var ticking = false;
        function fallbackCheck() {
            if (!pending.length) return;
            var vh = innerHeight;
            pending.slice().forEach(function (el) {
                var r = el.getBoundingClientRect();
                if (r.top < vh * .94 && r.bottom > 0) release(el);
            });
        }
        function onScroll() {
            if (ticking) return;
            ticking = true;
            requestAnimationFrame(function () { fallbackCheck(); ticking = false; });
        }
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll, { passive: true });
        setTimeout(fallbackCheck, 900);
    })();

    /* ================= 6. 卡片 3D 倾斜 ================= */
    (function tilt() {
        if (!desktop || reduced || !window.matchMedia('(hover: hover)').matches) return;
        $$('.post-card').forEach(function (card) {
            card.addEventListener('mousemove', function (e) {
                var r = card.getBoundingClientRect();
                var px = (e.clientX - r.left) / r.width - .5;
                var py = (e.clientY - r.top) / r.height - .5;
                card.style.transform =
                    'translateY(-8px) perspective(1000px) rotateX(' + (-py * 3.6).toFixed(2) +
                    'deg) rotateY(' + (px * 3.6).toFixed(2) + 'deg)';
            }, { passive: true });
            card.addEventListener('mouseleave', function () { card.style.transform = ''; }, { passive: true });
        });
    })();

    /* ================= 7. 鼠标跟随光晕 ================= */
    (function glow() {
        var g = $('#cursorGlow');
        if (!g || !desktop || reduced) return;
        var tx = innerWidth / 2, ty = innerHeight / 2, cx = tx, cy = ty;
        d.addEventListener('mousemove', function (e) {
            tx = e.clientX; ty = e.clientY;
            g.style.opacity = '1';
        }, { passive: true });
        d.addEventListener('mouseleave', function () { g.style.opacity = '0'; });
        (function loop() {
            cx += (tx - cx) * .07;
            cy += (ty - cy) * .07;
            g.style.transform = 'translate(' + cx + 'px,' + cy + 'px)';
            requestAnimationFrame(loop);
        })();
    })();

    /* ================= 8. 搜索（数据源 search.xml） ================= */
    (function search() {
        var mask = $('#searchMask');
        if (!mask) return;
        var input = $('#searchInput');
        var results = $('#searchResults');
        var entries = null;
        var timer = null;

        function open() {
            mask.classList.add('open');
            d.documentElement.style.overflow = 'hidden';
            setTimeout(function () { input.focus(); }, 60);
        }
        function close() {
            mask.classList.remove('open');
            d.documentElement.style.overflow = '';
        }

        $$('.js-search').forEach(function (b) { b.addEventListener('click', open); });
        mask.addEventListener('click', function (e) { if (e.target === mask) close(); });
        d.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') close();
            if ((e.key === '/' && !/INPUT|TEXTAREA/.test(d.activeElement.tagName)) ||
                (e.key.toLowerCase() === 'k' && (e.ctrlKey || e.metaKey))) {
                e.preventDefault(); open();
            }
        });

        function esc(s) {
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function ensureData(cb) {
            if (entries) return cb();
            fetch('/search.xml').then(function (r) { return r.text(); }).then(function (xml) {
                var doc = new DOMParser().parseFromString(xml, 'text/xml');
                entries = $$('entry', doc).map(function (en) {
                    var t = $('title', en), u = $('url', en) || $('link', en), c = $('content', en);
                    var tmp = d.createElement('div');
                    tmp.innerHTML = c ? c.textContent : '';
                    return {
                        title: t ? t.textContent.trim() : '',
                        url: u ? u.textContent.trim() : '#',
                        text: (tmp.textContent || '').replace(/\s+/g, ' ').trim()
                    };
                });
                cb();
            }).catch(function () {
                results.innerHTML = '<div class="search-hint">搜索数据加载失败，请刷新重试 🥲</div>';
            });
        }

        function render(keyword) {
            if (!keyword) {
                results.innerHTML = '<div class="search-hint">输入关键词，回车不必，实时搜索 ⚡</div>';
                return;
            }
            var kws = keyword.toLowerCase().split(/\s+/).filter(Boolean);
            var hits = entries.filter(function (en) {
                var hay = (en.title + ' ' + en.text).toLowerCase();
                return kws.every(function (k) { return hay.indexOf(k) > -1; });
            }).slice(0, 12);

            if (!hits.length) {
                results.innerHTML = '<div class="search-hint">没有找到「' + esc(keyword) + '」相关的文章 🥲</div>';
                return;
            }
            results.innerHTML = '<ul>' + hits.map(function (en) {
                var idx = en.text.toLowerCase().indexOf(kws[0]);
                var start = Math.max(0, idx - 24);
                var snippet = esc(en.text.slice(start, start + 130));
                kws.forEach(function (k) {
                    snippet = snippet.replace(new RegExp('(' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi'), '<mark>$1</mark>');
                });
                var title = esc(en.title);
                kws.forEach(function (k) {
                    title = title.replace(new RegExp('(' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi'), '<mark>$1</mark>');
                });
                return '<li><a href="' + en.url + '"><span class="sr-title">' + title +
                       '</span><span class="sr-snippet">' + snippet + '…</span></a></li>';
            }).join('') + '</ul>';
        }

        input.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(function () {
                ensureData(function () { render(input.value.trim()); });
            }, 160);
        });
    })();

    /* ================= 9. 阅读进度 + TOC 同步 ================= */
    (function reading() {
        var bar = $('#readProgress');
        var tocLinks = $$('.toc-list a');
        var heads = tocLinks.map(function (a) { return d.getElementById(decodeURIComponent(a.hash.slice(1))); });

        function onScroll() {
            var st = window.scrollY;
            if (bar) {
                var h = d.documentElement.scrollHeight - innerHeight;
                bar.style.width = (h > 0 ? (st / h) * 100 : 0) + '%';
            }
            if (heads.length) {
                var active = -1;
                heads.forEach(function (hd, i) { if (hd && hd.getBoundingClientRect().top < 140) active = i; });
                tocLinks.forEach(function (a, i) { a.classList.toggle('toc-active', i === active); });
            }
        }
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    })();

    /* ================= 10. 代码块增强（Mac 灯 / 语言 / 复制） ================= */
    (function codeBlocks() {
        var blocks = $$('#articleContent figure.highlight, #articleContent pre');
        blocks.forEach(function (b) {
            var lang = '';
            var m = b.className.match(/highlight\s+(\w+)/);
            if (m) lang = m[1];
            if (!lang) {
                var code = b.querySelector('code');
                var cm = code && code.className.match(/language-(\w+)/);
                if (cm) lang = cm[1];
                else lang = 'code';
            }
            b.classList.add('has-dots');

            var chip = d.createElement('span');
            chip.className = 'code-lang-chip';
            chip.textContent = lang;
            b.appendChild(chip);

            var btn = d.createElement('button');
            btn.className = 'code-copy-btn';
            btn.type = 'button';
            btn.textContent = '复制';
            btn.addEventListener('click', function () {
                var codeEl = b.querySelector('pre') || b.querySelector('code');
                var text = codeEl ? codeEl.innerText : '';
                function done() {
                    btn.textContent = '已复制 ✓';
                    btn.classList.add('done');
                    setTimeout(function () { btn.textContent = '复制'; btn.classList.remove('done'); }, 1600);
                }
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(done);
                } else {
                    var ta = d.createElement('textarea');
                    ta.value = text;
                    d.body.appendChild(ta);
                    ta.select();
                    try { d.execCommand('copy'); } catch (e) { /* ignore */ }
                    d.body.removeChild(ta);
                    done();
                }
            });
            b.appendChild(btn);
        });
    })();

    /* ================= 11. 文章图片灯箱 ================= */
    (function gallery() {
        var wrap = $('#articleContent');
        if (!wrap || !window.jQuery || !(window.jQuery.fn && window.jQuery.fn.lightGallery)) return;
        $$('img', wrap).forEach(function (img) {
            if (img.closest('.img-item')) return;
            var div = d.createElement('div');
            div.className = 'img-item';
            div.setAttribute('data-src', img.getAttribute('src'));
            img.parentNode.insertBefore(div, img);
            div.appendChild(img);
        });
        try {
            window.jQuery('#articleContent').lightGallery({
                selector: '.img-item',
                download: false,
                actualSize: false
            });
        } catch (e) { /* ignore */ }
    })();

    /* ================= 12. 返回顶部 ================= */
    (function backtop() {
        var btn = $('#backTop');
        if (!btn) return;
        window.addEventListener('scroll', function () {
            btn.classList.toggle('show', window.scrollY > 420);
        }, { passive: true });
        btn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
        });
    })();
})();
