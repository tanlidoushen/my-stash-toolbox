// ================ 卡片渲染模块 ================
const CardRenderer = {

    getThumbnailUrl(scene) {
        if (!scene.images || !scene.images.length) return '';
        return `${Config.BASE_URL}/images/${scene.images[0].id}?maxheight=400`;
    },

    getPerformerAvatarUrl(performer) {
        if (!performer?.images?.length) return '';
        return `${Config.BASE_URL}/images/${performer.images[0].id}?maxheight=200`;
    },

    getSceneUrl(scene) {
        return `${Config.BASE_URL}/scenes/${scene.id}`;
    },

    getPerformerUrl(performerId) {
        return `${Config.BASE_URL}/performers/${performerId}`;
    },

    getStudioUrl(scene) {
        return scene.studio ? `${Config.BASE_URL}/studios/${scene.studio.id}` : '';
    },

    esc(str) {
        const el = document.createElement('span');
        el.textContent = str || '';
        return el.innerHTML;
    },

    formatDuration(seconds) {
        if (!seconds) return '';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        return `${m}:${String(s).padStart(2, '0')}`;
    },

    formatDate(dateStr) {
        if (!dateStr) return '';
        return dateStr.slice(0, 10);
    },

    // ---- 指纹信息 ----

    getTotalSubmissions(fingerprints) {
        if (!fingerprints || !fingerprints.length) return 0;
        return fingerprints.reduce((sum, fp) => sum + (fp.submissions || 0), 0);
    },

    getFingerprintColor(totalSubmissions) {
        const T = Config.THRESHOLDS.SUBMISSIONS;
        if (totalSubmissions > T.HIGH) return Config.COLORS.FINGERPRINT.HIGH;
        if (totalSubmissions > T.MEDIUM) return Config.COLORS.FINGERPRINT.MEDIUM;
        if (totalSubmissions > T.LOW) return Config.COLORS.FINGERPRINT.LOW;
        return Config.COLORS.FINGERPRINT.DEFAULT;
    },

    renderFingerprintBar(fingerprintCount, totalSubmissions) {
        const color = this.getFingerprintColor(totalSubmissions);
        return `
            <div class="fingerprint-info sewf-fingerprint" style="
                background: linear-gradient(135deg, ${color} 0%, ${color}99 100%);
                color: white; padding: 6px 10px; border-radius: 4px; margin-top: 8px;
                font-size: 12px; display: flex; justify-content: space-between; align-items: center;
            ">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0;">
                        <path d="M12 0C5.37 0 0 5.37 0 12s5.37 12 12 12 12-5.37 12-12S18.63 0 12 0zm0 22C6.48 22 2 17.52 2 12S6.48 2 12 2s10 4.48 10 10-4.48 10-10 10zm5-8c0 2.76-2.24 5-5 5s-5-2.24-5-5 2.24-5 5-5 5 2.24 5 5zm-5 3c1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3 1.34 3 3 3z"/>
                    </svg>
                    <span>指纹: ${fingerprintCount}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0;">
                        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                    </svg>
                    <span>提交: ${totalSubmissions}</span>
                </div>
            </div>`;
    },

    // ---- 外部链接按钮 ----

    renderUrlButtons(urls) {
        if (!urls || !urls.length) return '';
        const valid = urls.filter(u => u.url && u.url.trim()).slice(0, 5);
        if (!valid.length) return '';

        const btns = valid.map(u => {
            const url = u.url.trim();
            const domain = Utils.getDomainFromUrl(url);
            const iconUrl = domain !== '链接'
                ? `${Config.BASE_URL}/favicon/${domain}`
                : '';
            return `
                <a href="${url}" target="_blank" title="${url}" style="
                    display: inline-flex; align-items: center; justify-content: center;
                    width: 28px; height: 28px; border-radius: 4px;
                    background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
                    color: white; text-decoration: none;
                    transition: all 0.2s ease; border: 1px solid rgba(255,255,255,0.2);
                " onmouseover="this.style.transform='scale(1.1)';this.style.boxShadow='0 2px 8px rgba(0,0,0,0.3)'"
                   onmouseout="this.style.transform='scale(1)';this.style.boxShadow='none'">
                    ${iconUrl
                        ? `<img src="${iconUrl}" alt="${domain}" style="width:16px;height:16px;" onerror="this.outerHTML='🔗'">`
                        : '<span style="font-size:14px;">🔗</span>'}
                </a>`;
        }).join('');

        return `<div style="display: flex; align-items: center; gap: 4px; margin: 4px 0; justify-content: center; flex-wrap: wrap;">${btns}</div>`;
    },

    // ---- 演员列表 ----

    calculateAgeAtScene(birthDate, sceneDate) {
        if (!birthDate || !sceneDate) return null;
        try {
            const birth = new Date(birthDate);
            const scene = new Date(sceneDate);
            let age = scene.getFullYear() - birth.getFullYear();
            const m = scene.getMonth() - birth.getMonth();
            if (m < 0 || (m === 0 && scene.getDate() < birth.getDate())) age--;
            return age;
        } catch { return null; }
    },

    getYoungestFemaleAge(performers, sceneDate) {
        let youngest = null;
        for (const p of performers) {
            const perf = p.performer;
            if (perf.gender === 'FEMALE' && perf.birth_date) {
                const age = this.calculateAgeAtScene(perf.birth_date, sceneDate);
                if (age !== null && (youngest === null || age < youngest)) youngest = age;
            }
        }
        return youngest;
    },

    countFemalePerformers(performers) {
        return performers.filter(p => p.performer.gender === 'FEMALE').length;
    },

    sortPerformers(performers) {
        return [...performers].sort((a, b) => {
            const pa = a.performer, pb = b.performer;
            if (pa.gender === 'FEMALE' && pb.gender !== 'FEMALE') return -1;
            if (pa.gender !== 'FEMALE' && pb.gender === 'FEMALE') return 1;
            if (pa.gender === pb.gender) {
                if (pa.is_favorite && !pb.is_favorite) return -1;
                if (!pa.is_favorite && pb.is_favorite) return 1;
                return pa.name.localeCompare(pb.name);
            }
            if (pa.gender === 'MALE' && pb.gender !== 'MALE') return 1;
            if (pa.gender !== 'MALE' && pb.gender === 'MALE') return -1;
            return pa.name.localeCompare(pb.name);
        });
    },

    getPerformerAvatarBg(performer) {
        const C = Config.COLORS.PERFORMER_AVATAR;
        if (performer.is_favorite) {
            if (performer.gender === 'FEMALE') return C.FAVORITE_FEMALE;
            if (performer.gender === 'MALE') return C.FAVORITE_MALE;
            return C.FAVORITE_OTHER;
        }
        if (performer.gender === 'FEMALE') return C.FEMALE;
        if (performer.gender === 'MALE') return C.MALE;
        return C.OTHER;
    },

    // 方形头像 + 星标 + 国旗 (与 enhancer 一致)
    renderPerformersList(performers, sceneDate) {
        if (!performers || !performers.length) return '';
        const sorted = this.sortPerformers(performers);

        const items = sorted.map(p => {
            const perf = p.performer;
            const avatarUrl = this.getPerformerAvatarUrl(perf);
            const age = this.calculateAgeAtScene(perf.birth_date, sceneDate);
            const bg = this.getPerformerAvatarBg(perf);
            const profileUrl = this.getPerformerUrl(perf.id);
            const genderIcon = perf.gender === 'FEMALE' ? '♀️' : perf.gender === 'MALE' ? '♂️' : '⚧️';

            // tooltip
            let tooltip = perf.name;
            if (perf.gender === 'FEMALE') tooltip += ' (♀女)';
            else if (perf.gender === 'MALE') tooltip += ' (♂男)';
            else tooltip += ' (⚧跨性别)';
            if (perf.country) tooltip += ' - ' + perf.country;
            if (age !== null) tooltip += ` - 年龄：${age} 岁`;
            if (perf.is_favorite) tooltip += ' - ⭐收藏';

            // 国旗
            let flagHtml = '';
            if (perf.country) {
                const countryCode = perf.country.toLowerCase();
                flagHtml = `
                    <span class="country-flag" style="
                        position: absolute; bottom: -3px; right: -5px;
                        width: 30px; height: 20px; transform: scale(0.7);
                    ">
                        <img src="${Config.BASE_URL}/flag/${countryCode}.svg" loading="lazy"
                             alt="${perf.country}"
                             style="width: 100%; height: 100%; object-fit: cover;">
                    </span>`;
            }

            // 星标
            const favIcon = perf.is_favorite ? `
                <span class="favorite-icon" style="
                    position: absolute; top: 2px; right: 2px;
                    background: gold; width: 16px; height: 16px; border-radius: 50%;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 10px; color: black;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
                ">⭐</span>` : '';

            // 头像图片 or fallback
            const avatarInner = avatarUrl
                ? `<img src="${avatarUrl}" loading="lazy" alt="${this.esc(perf.name)}"
                        style="width:100%;height:100%;object-fit:cover;object-position:top;display:block;"
                        onerror="this.onerror=null;this.style.display='none';this.parentNode.querySelector('.avatar-fallback').style.display='flex';">`
                : '';

            return `
                <li class="vsc-performer-card sewf-performer-card" style="list-style: none; margin: 0 3px; width: 70px;">
                    <a href="${profileUrl}" target="_blank" title="${tooltip}" style="display: block; text-decoration: none; color: inherit;">
                        <div class="performer-avatar vsc-performer-avatar sewf-performer-avatar" style="
                            width: 70px; height: 90px; overflow: hidden; position: relative;
                            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                            background: ${bg};
                        ">
                            ${avatarInner}
                            <div class="avatar-fallback" style="
                                width: 100%; height: 100%;
                                display: ${avatarUrl ? 'none' : 'flex'};
                                align-items: center; justify-content: center;
                                color: white; font-weight: bold; font-size: 20px;
                                background: ${bg};
                            ">${perf.name.charAt(0).toUpperCase()}</div>
                            ${flagHtml}
                            ${favIcon}
                        </div>
                        <div class="performer-info" style="text-align:center;padding:4px 0;font-size:12px;line-height:1.3;">
                            <div class="performer-name" style="font-weight:bold;color:white;text-shadow:1px 1px 2px rgba(0,0,0,0.8);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                                ${this.esc(perf.name)}
                            </div>
                            <div style="display:flex;justify-content:center;align-items:center;gap:4px;margin:2px 0;">
                                <span class="performer-gender" style="font-size:14px;">${genderIcon}</span>
                                ${age !== null ? `<span class="performer-age" style="color:white;text-shadow:1px 1px 2px rgba(0,0,0,0.8);font-size:11px;">${age}岁</span>` : ''}
                            </div>
                        </div>
                    </a>
                </li>`;
        }).join('');

        // 统计
        const femaleCount = this.countFemalePerformers(performers);
        const otherCount = performers.filter(p => p.performer.gender !== 'FEMALE' && p.performer.gender !== 'MALE').length;
        const maleCount = performers.length - femaleCount - otherCount;
        const favCount = performers.filter(p => p.performer.is_favorite).length;

        let stats = '';
        if (femaleCount > 0) stats += `♀️${femaleCount}`;
        if (maleCount > 0) stats += `${stats ? ' ' : ''}♂️${maleCount}`;
        if (otherCount > 0) stats += `${stats ? ' ' : ''}⚧️${otherCount}`;
        if (favCount > 0) stats += `${stats ? ' ' : ''}⭐${favCount}`;

        return `
            <div class="performer-section" style="margin-top: 10px;">
                <div style="font-size: 12px; color: #666; margin-bottom: 6px; font-weight: bold; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="#666">
                            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                        演员 (${performers.length})
                    </div>
                    <div style="font-size: 11px; color: #999;">${stats}</div>
                </div>
                <ul class="vsc-performers-list sewf-performers-list" style="
                    display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0;
                    justify-content: flex-start; list-style: none;
                ">
                    ${items}
                </ul>
            </div>`;
    },

    // ---- 完整卡片 ----

    renderCard(scene) {
        const thumbUrl = this.getThumbnailUrl(scene);
        const sceneUrl = this.getSceneUrl(scene);
        const totalSub = this.getTotalSubmissions(scene.fingerprints);
        const fpCount = scene.fingerprints ? scene.fingerprints.length : 0;
        const femaleCount = this.countFemalePerformers(scene.performers);
        const hasFemale = femaleCount > 0;

        const durationStr = this.formatDuration(scene.duration);
        const dateStr = this.formatDate(scene.date);
        const studioUrl = this.getStudioUrl(scene);

        // 工作室链接 (与 waterfall 一致)
        const studioHtml = scene.studio
            ? `<a class="float-end text-truncate SceneCard-studio-name" href="${studioUrl}"><svg data-prefix="fas" data-icon="video" class="svg-inline--fa fa-video fa-icon me-1" role="img" viewBox="0 0 576 512"><path fill="currentColor" d="M96 64c-35.3 0-64 28.7-64 64l0 256c0 35.3 28.7 64 64 64l256 0c35.3 0 64-28.7 64-64l0-256c0-35.3-28.7-64-64-64L96 64zM464 336l73.5 58.8c4.2 3.4 9.4 5.2 14.8 5.2 13.1 0 23.7-10.6 23.7-23.7l0-240.6c0-13.1-10.6-23.7-23.7-23.7-5.4 0-10.6 1.8-14.8 5.2L464 176 464 336z"></path></svg>${this.esc(scene.studio.name)}</a>`
            : '';

        const col = Utils.createElement('div', { className: 'col-3', 'data-scene-id': scene.id });
        col.setAttribute('data-fingerprint-count', fpCount);
        col.setAttribute('data-total-submissions', totalSub);
        col.setAttribute('data-performer-count', scene.performers ? scene.performers.length : 0);
        col.setAttribute('data-female-performer-count', femaleCount);
        col.dataset.hasFemale = hasFemale ? 'true' : 'false';

        const imgSrc = thumbUrl || '';
        const imgSrcSet = thumbUrl ? thumbUrl.replace('maxheight=400', 'maxheight=800') : '';

        const fpHtml = this.renderFingerprintBar(fpCount, totalSub);
        const urlHtml = this.renderUrlButtons(scene.urls);
        const perfHtml = this.renderPerformersList(scene.performers, scene.date);

        const codeHtml = scene.code
            ? `<div style="font-size:11px;color:#aaa;margin-top:2px;font-family:monospace;">${this.esc(scene.code)}</div>`
            : '';

        col.innerHTML = `
            <div class="SceneCard card">
                <div class="SceneCard-body card-body">
                    <a class="SceneCard-image" href="/scenes/${scene.id}">
                        ${imgSrc
                            ? `<img alt="${this.esc(scene.title)}" class="horizontal-img" src="${imgSrc}" srcset="${imgSrcSet} 600w" loading="lazy">`
                            : `<div style="width:100%;aspect-ratio:16/9;background:#e9ecef;display:flex;align-items:center;justify-content:center;color:#999;font-size:32px;">🎬</div>`}
                    </a>
                </div>
                <div class="card-footer">
                    <div class="d-flex">
                        <a class="text-truncate w-100" title="${this.esc(scene.title)}" href="/scenes/${scene.id}">
                            <h6 class="text-truncate">${this.esc(scene.title || '无标题')}</h6>
                        </a>
                        <span class="text-muted">${durationStr}</span>
                    </div>
                    <div class="text-muted">${studioHtml}<strong>${dateStr}</strong></div>
                    ${codeHtml}
                    ${fpHtml}
                    ${urlHtml}
                    ${perfHtml}
                </div>
            </div>`;

        return col;
    },
};