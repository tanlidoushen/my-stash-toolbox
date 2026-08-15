// ================ API 模块 ================
const API = {
    gqlRequest(query, variables) {
        return fetch(Config.API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'ApiKey': Config.API_KEY,
            },
            body: JSON.stringify({ query, variables }),
        }).then(res => {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        });
    },

    buildFilter(pageInfo) {
        const cond = [];
        switch (pageInfo.type) {
            case Config.PAGE_TYPES.STUDIO:
                cond.push(`parentStudio: "${pageInfo.id}"`);
                this._addConditionalTag(cond, pageInfo.extraTagId);
                this._addFavoriteFilter(cond, pageInfo.favoriteType);
                break;
            case Config.PAGE_TYPES.TAG:
                cond.push(`tags: { value: ["${pageInfo.id}"], modifier: INCLUDES }`);
                break;
            case Config.PAGE_TYPES.PERFORMER:
                cond.push(`performers: { value: ["${pageInfo.id}"], modifier: INCLUDES }`);
                this._addConditionalTag(cond, pageInfo.extraTagId);
                this._addConditionalStudios(cond, pageInfo.extraStudioIds);
                this._addFavoriteFilter(cond, pageInfo.favoriteType);
                break;
            case Config.PAGE_TYPES.SCENES:
                this._addConditionalTag(cond, pageInfo.extraTagId);
                this._addConditionalStudios(cond, pageInfo.extraStudioIds);
                this._addFavoriteFilter(cond, pageInfo.favoriteType);
                break;
        }
        return cond.join(',\n            ');
    },

    _addFavoriteFilter(cond, favoriteType) {
        if (favoriteType) {
            // ?favorite=performer|studio|all → favorites: PERFORMER|STUDIO|ALL
            cond.push(`favorites: ${favoriteType}`);
        }
    },

    _addConditionalTag(cond, tagId) {
        if (tagId) {
            cond.push(`tags: { value: ["${tagId}"], modifier: INCLUDES }`);
        }
    },

    _addConditionalStudios(cond, studioIds) {
        if (studioIds && studioIds.length > 0) {
            cond.push(`studios: { value: ${JSON.stringify(studioIds)}, modifier: INCLUDES }`);
        }
    },

    buildSort(pageInfo) {
        return pageInfo.sortType || 'DATE';
    },

    async fetchScenes(pageInfo, page, perPage) {
        const sortField = this.buildSort(pageInfo);
        const filterStr = this.buildFilter(pageInfo);

        const query = `
        query FindScenes($page: Int!, $per_page: Int!) {
            queryScenes(input: {
                page: $page,
                per_page: $per_page,
                sort: ${sortField},
                direction: DESC,
                ${filterStr}
            }) {
                count
                scenes {
                    id
                    code
                    title
                    date
                    duration
                    studio { id name }
                    images { id }
                    fingerprints {
                        hash
                        algorithm
                        submissions
                        reports
                    }
                    urls {
                        url
                    }
                    performers {
                        performer {
                            id
                            name
                            gender
                            country
                            is_favorite
                            birth_date
                            age
                            images { id }
                        }
                    }
                }
            }
        }`;

        const variables = { page, per_page: perPage };
        const result = await this.gqlRequest(query, variables);
        if (result.errors || !result.data?.queryScenes) {
            throw new Error('GraphQL 返回数据格式错误');
        }
        return result.data.queryScenes;
    },
};