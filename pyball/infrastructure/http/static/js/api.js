// Minimal JSON API client shared by the match and manage pages.

export class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `HTTP ${status}`);
        this.status = status;
        this.detail = detail;
    }
}

// Perform a JSON request. Resolves with the parsed body; throws ApiError on
// any non-2xx response (status 0 = network failure).
export async function request(method, path, body = undefined) {
    let res;
    try {
        res = await fetch(path, {
            method,
            headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
    } catch {
        throw new ApiError(0, 'network');
    }
    if (res.status === 401) {
        renderUnauthorized();
        throw new ApiError(401, 'unauthorized');
    }
    if (!res.ok) {
        let detail = res.statusText;
        try { detail = (await res.json()).detail || detail; } catch { /* keep statusText */ }
        throw new ApiError(res.status, detail);
    }
    return res.json();
}

export const get = (path) => request('GET', path);
export const post = (path, body) => request('POST', path, body);
export const del = (path) => request('DELETE', path);

function renderUnauthorized() {
    document.body.innerHTML = '<h1 style="font-family:system-ui;color:#f8fafc;background:#0f172a;height:100vh;display:flex;align-items:center;justify-content:center;margin:0;">Acceso no autorizado</h1>';
}
