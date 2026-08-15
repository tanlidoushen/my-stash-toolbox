// ================ 样式模块（深色玻璃风格） ================
const Styles = {
    add() {
        const old = document.getElementById('sewf-styles');
        if (old) old.remove();

        const style = document.createElement('style');
        style.id = 'sewf-styles';
        style.textContent = `
            /* ========== 卡片动画 ========== */
            .col-3 {
                transition: opacity 0.3s ease;
            }
            .col-3[style*="display: none"] {
                opacity: 0.3;
            }

            .fingerprint-info {
                transition: all 0.3s ease;
                cursor: help;
            }
            .fingerprint-info:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }

            .performer-section .vsc-performer-avatar:hover {
                transform: scale(1.1);
                transition: transform 0.2s ease;
            }

            /* ========== 工具栏容器（深色玻璃） ========== */
            .sewf-toolbar {
                background: rgba(25, 25, 38, 0.94);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 10px 16px;
                margin: 12px 0;
                box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
            }

            /* ========== 上排行布局 ========== */
            .sewf-toolbar-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 10px;
            }

            .sewf-toolbar-left {
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
            }

            .sewf-toolbar-btns {
                display: flex;
                gap: 6px;
                align-items: center;
                flex-wrap: wrap;
            }

            .sewf-toolbar-right {
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
            }

            /* ========== 排序/过滤按钮 ========== */
            .sewf-tb-btn {
                padding: 5px 14px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.85);
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.15s ease;
                white-space: nowrap;
            }
            .sewf-tb-btn:hover {
                background: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.2);
            }
            .sewf-tb-btn.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-color: transparent;
                color: #fff;
                font-weight: 600;
            }
            .sewf-tb-btn.active:hover {
                opacity: 0.92;
            }

            /* ========== 标签 / 文字 ========== */
            .sewf-tb-tag {
                background: rgba(255, 255, 255, 0.1);
                padding: 2px 10px;
                border-radius: 5px;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.8);
                white-space: nowrap;
            }
            .sewf-tb-count {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
            }
            .sewf-tb-count b {
                color: rgba(255, 255, 255, 0.95);
            }

            .sewf-tb-label {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }

            /* ========== 下拉选择 ========== */
            .sewf-tb-select {
                padding: 3px 8px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
                font-size: 12px;
                cursor: pointer;
                outline: none;
            }
            .sewf-tb-select:hover {
                border-color: rgba(255, 255, 255, 0.25);
            }
            .sewf-tb-select:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.3);
            }
            .sewf-tb-select option {
                background: #1e1e2e;
                color: #fff;
            }

            /* ========== 分割线 ========== */
            .sewf-toolbar-divider {
                height: 1px;
                background: rgba(255, 255, 255, 0.06);
                margin: 8px 0;
            }

            /* ========== 分页导航行 ========== */
            .sewf-toolbar-nav {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 4px;
                flex-wrap: wrap;
            }

            /* ========== 导航按钮 ========== */
            .sewf-tb-nav-btn {
                min-width: 32px;
                height: 30px;
                padding: 0 8px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.85);
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.15s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .sewf-tb-nav-btn:hover {
                background: rgba(255, 255, 255, 0.14);
                border-color: rgba(255, 255, 255, 0.22);
            }
            .sewf-tb-nav-btn.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-color: transparent;
                color: #fff;
                font-weight: 700;
            }
            .sewf-tb-nav-btn.disabled {
                opacity: 0.3;
                cursor: not-allowed;
            }
            .sewf-tb-nav-btn.disabled:hover {
                background: rgba(255, 255, 255, 0.06);
                border-color: rgba(255, 255, 255, 0.12);
            }

            /* ========== 省略号 ========== */
            .sewf-tb-dots {
                color: rgba(255, 255, 255, 0.5);
                padding: 0 4px;
                font-size: 14px;
            }

            /* ========== 跳转输入 ========== */
            .sewf-tb-jump {
                display: flex;
                align-items: center;
                gap: 4px;
                margin-left: 10px;
                padding-left: 10px;
                border-left: 1px solid rgba(255, 255, 255, 0.1);
            }
            .sewf-tb-input {
                width: 56px;
                padding: 3px 6px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                text-align: center;
                outline: none;
                -moz-appearance: textfield;
            }
            .sewf-tb-input::-webkit-inner-spin-button,
            .sewf-tb-input::-webkit-outer-spin-button {
                -webkit-appearance: none;
                margin: 0;
            }
            .sewf-tb-input:hover {
                border-color: rgba(255, 255, 255, 0.25);
            }
            .sewf-tb-input:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.3);
            }

            .sewf-tb-jump-btn {
                padding: 3px 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.85);
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.15s ease;
            }
            .sewf-tb-jump-btn:hover {
                background: rgba(255, 255, 255, 0.14);
                border-color: rgba(255, 255, 255, 0.22);
            }

            /* ========== 底部分页（暗色统一） ========== */
            .sewf-pagination {
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: nowrap;
                gap: 16px;
                background: rgba(25, 25, 38, 0.94) !important;
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 12px !important;
                padding: 10px 16px !important;
                margin: 12px 0 !important;
                box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
            }
            .sewf-pagination span {
                color: rgba(255, 255, 255, 0.7);
            }
            .sewf-pagination span b {
            .sewf-pagination > div {
                display: flex !important;
                align-items: center !important;
                gap: 12px !important;
                flex-wrap: nowrap !important;
            }
                color: rgba(255, 255, 255, 0.95);
            }
            .sewf-pagination select {
                padding: 3px 8px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
                font-size: 12px;
                cursor: pointer;
                outline: none;
            }
            .sewf-pagination select:hover {
                border-color: rgba(255, 255, 255, 0.25);
            }
            .sewf-pagination select:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.3);
            }
            .sewf-pagination select option {
                background: #1e1e2e;
                color: #fff;
            }
/* ========== 分页按钮（暗色统一） ========== */
            .sewf-pg-btn {
                min-width: 32px;
                height: 30px;
                padding: 0 8px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.85);
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.15s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .sewf-pg-btn:hover {
                background: rgba(255, 255, 255, 0.14);
                border-color: rgba(255, 255, 255, 0.22);
            }
            .sewf-pg-btn.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-color: transparent;
                color: #fff;
                font-weight: 700;
                box-shadow: 0 0 14px rgba(102, 126, 234, 0.5);
            }
            .sewf-pg-btn.active:hover {
                box-shadow: 0 0 20px rgba(102, 126, 234, 0.65);
            }
            .sewf-pg-btn.disabled {
                opacity: 0.3;
                cursor: not-allowed;
            }
            .sewf-pg-btn.disabled:hover {
                background: rgba(255, 255, 255, 0.06);
                border-color: rgba(255, 255, 255, 0.12);
            }
            .sewf-pg-dots {
                display: flex;
                align-items: center;
                color: rgba(255, 255, 255, 0.45);
                padding: 0 4px;
                font-size: 14px;
            }
            .sewf-pg-jump {
                display: flex;
                align-items: center;
                gap: 4px;
                margin-left: 8px;
                padding-left: 8px;
                border-left: 1px solid rgba(255, 255, 255, 0.1);
                flex-shrink: 0;
            }
            .sewf-pg-jump input[type="number"] {
                width: 56px;
                padding: 3px 6px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                text-align: center;
                outline: none;
                -moz-appearance: textfield;
            }
            .sewf-pg-jump input[type="number"]:hover {
                border-color: rgba(255, 255, 255, 0.25);
            }
            .sewf-pg-jump input[type="number"]:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.3);
            }
            .sewf-pg-jump input[type="number"]::-webkit-inner-spin-button,
            .sewf-pg-jump input[type="number"]::-webkit-outer-spin-button {
                -webkit-appearance: none;
                margin: 0;
            }
            .sewf-pg-jump-btn {
                padding: 3px 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.85);
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.15s ease;
                flex-shrink: 0;
            }
            .sewf-pg-jump-btn:hover {
                background: rgba(255, 255, 255, 0.14);
                border-color: rgba(255, 255, 255, 0.22);
            }
/* ========== 加载/错误提示 ========== */
            .sewf-loading {
                color: rgba(255, 255, 255, 0.7);
                text-align: center;
                padding: 40px 0;
                font-size: 15px;
            }
            .sewf-error {
                color: #f5576c;
                text-align: center;
                padding: 40px 0;
                font-size: 15px;
            }

            /* ========== 隐藏原生分页（排序/收藏筛选控件保留） ========== */
            .ms-auto.d-flex:has(.pagination) {
                display: none !important;
            }
        `;
        document.head.appendChild(style);
    },
};






