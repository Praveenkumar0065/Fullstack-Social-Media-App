import { firebaseApp, auth, db, storage, firebaseReady } from './firebase-config.js';

const $ = (s, p = document) => p.querySelector(s);
const $$ = (s, p = document) => [...p.querySelectorAll(s)];

const state = {
	user: null,
	token: localStorage.getItem('authToken') || '',
	refreshToken: localStorage.getItem('refreshToken') || '',
	chatRoom: localStorage.getItem('chatRoom') || 'global',
	lang: localStorage.getItem('lang') || 'en',
	theme: localStorage.getItem('theme') || 'light',
	rate: { last: 0, count: 0 },
};

function resolveApiBase() {
	const fromWindow = String(window.SOCIALSPHERE_API_BASE || '').trim();
	if (fromWindow) return fromWindow.replace(/\/$/, '');
	const fromLocalStorage = String(localStorage.getItem('apiBase') || '').trim();
	if (fromLocalStorage) return fromLocalStorage.replace(/\/$/, '');
	return location.port === '5500' ? 'http://127.0.0.1:8000/api' : `${location.origin}/api`;
}

const API_BASE = resolveApiBase();

const i18n = {
	en: { hero_title: 'Share moments that matter.', hero_sub: 'Create posts, connect with friends, and discover trending content worldwide.', get_started: 'Get Started', login: 'Login', signup: 'Sign Up' },
	es: { hero_title: 'Comparte momentos que importan.', hero_sub: 'Crea publicaciones, conecta con amigos y descubre tendencias globales.', get_started: 'Comenzar', login: 'Iniciar sesion', signup: 'Registrarse' },
};

const routes = {
	'/': renderLanding,
	'/login': renderLogin,
	'/signup': renderSignup,
	'/feed': renderFeed,
	'/explore': renderExplore,
	'/profile': renderProfile,
	'/notifications': renderNotifications,
	'/messages': renderMessages,
	'/admin': renderAdmin,
};

let chatSocket = null;
let chatReconnectTimer = null;
let chatReconnectAttempt = 0;

function toast(msg, ok = true) {
	const d = document.createElement('div');
	d.className = 'card';
	d.style.position = 'fixed';
	d.style.right = '12px';
	d.style.bottom = '12px';
	d.style.zIndex = 99;
	d.style.borderColor = ok ? '#86efac' : '#fecaca';
	d.textContent = msg;
	document.body.appendChild(d);
	setTimeout(() => d.remove(), 2200);
}

function t(k) { return i18n[state.lang]?.[k] || k; }
function applyI18n() { $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); }); $('#langBtn').textContent = state.lang.toUpperCase(); }
function navigate(path) { history.pushState({}, '', path); router(); }

window.addEventListener('popstate', router);
document.addEventListener('click', (e) => { const b = e.target.closest('[data-link]'); if (b) { e.preventDefault(); navigate(b.dataset.link); } });

function applyTheme() {
	document.documentElement.style.filter = state.theme === 'dark' ? 'invert(1) hue-rotate(180deg)' : 'none';
	$('#themeBtn').textContent = state.theme === 'dark' ? 'Sun' : 'Moon';
}

$('#themeBtn').onclick = () => { state.theme = state.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('theme', state.theme); applyTheme(); };
$('#langBtn').onclick = () => { state.lang = state.lang === 'en' ? 'es' : 'en'; localStorage.setItem('lang', state.lang); applyI18n(); router(); };
$('#logoutBtn').onclick = async () => {
	try {
		if (state.token && state.refreshToken) {
			try {
				await api('/auth/logout', {
					method: 'POST',
					body: JSON.stringify({ refresh_token: state.refreshToken }),
				});
			} catch {
				// Continue local logout even if revoke fails due to network or expired session.
			}
		}
		if (firebaseReady && auth) await auth.signOut();
		localStorage.removeItem('mockUser');
		localStorage.removeItem('authToken');
		localStorage.removeItem('refreshToken');
		state.user = null;
		state.token = '';
		state.refreshToken = '';
		updateAuthUI();
		navigate('/');
	} catch {
		toast('Logout failed', false);
	}
};

function updateAuthUI() {
	const authed = !!state.user;
	$$('.authed').forEach((e) => e.classList.toggle('hidden', !authed));
	$$('.admin-only').forEach((e) => e.classList.toggle('hidden', !(authed && state.user?.role === 'admin')));
}

function setView(tid) {
	const tpl = $(tid);
	$('#view').innerHTML = '';
	$('#view').appendChild(tpl.content.cloneNode(true));
	applyI18n();
}

async function api(path, opt = {}) {
	try {
		const headers = { 'Content-Type': 'application/json', ...(opt.headers || {}) };
		if (state.token && !path.startsWith('http')) headers.Authorization = `Bearer ${state.token}`;
		const r = await fetch(path.startsWith('http') ? path : `${API_BASE}${path}`, { ...opt, headers });
		if (!r.ok) {
			let msg = `API ${r.status}`;
			try { const err = await r.json(); msg = err.detail || msg; } catch {}
			if (r.status === 401 && !path.startsWith('/auth/refresh')) {
				const refreshed = await refreshAuthToken();
				if (refreshed) return api(path, opt);
				state.token = '';
				state.refreshToken = '';
				localStorage.removeItem('authToken');
				localStorage.removeItem('refreshToken');
			}
			throw new Error(msg);
		}
		if (r.status === 204) return null;
		return await r.json();
	} catch (e) {
		throw new Error(e.message || 'Network error');
	}
}

async function refreshAuthToken() {
	if (!state.refreshToken) return false;
	try {
		const r = await fetch(`${API_BASE}/auth/refresh`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ refresh_token: state.refreshToken }),
		});
		if (!r.ok) return false;
		const data = await r.json();
		state.token = data.access_token || '';
		state.refreshToken = data.refresh_token || '';
		if (!state.token || !state.refreshToken) return false;
		localStorage.setItem('authToken', state.token);
		localStorage.setItem('refreshToken', state.refreshToken);
		return true;
	} catch {
		return false;
	}
}

function setChatStatus(label, cls) {
	const el = $('#chatStatus');
	if (!el) return;
	el.textContent = label;
	el.className = `pill ${cls || ''}`.trim();
}

function clearChatReconnect() {
	if (chatReconnectTimer) {
		clearTimeout(chatReconnectTimer);
		chatReconnectTimer = null;
	}
}

function getChatSocketUrl() {
	const base = API_BASE.replace(/\/api\/?$/, '');
	const token = encodeURIComponent(state.token || '');
	const room = encodeURIComponent(state.chatRoom || 'global');
	if (base.startsWith('https://')) return `${base.replace('https://', 'wss://')}/ws/chat?token=${token}&room=${room}`;
	if (base.startsWith('http://')) return `${base.replace('http://', 'ws://')}/ws/chat?token=${token}&room=${room}`;
	const proto = location.protocol === 'https:' ? 'wss' : 'ws';
	return `${proto}://${location.host}/ws/chat?token=${token}&room=${room}`;
}

function closeChatSocket() {
	clearChatReconnect();
	if (chatSocket && chatSocket.readyState <= 1) chatSocket.close();
	chatSocket = null;
}

function appendChatMessage(text, who = 'room', created = Date.now()) {
	const box = $('#chatMessages');
	if (!box) return;
	const me = currentUser() || {};
	const own = who && (who === me.name || who === me.email);
	const system = who === 'system';
	const item = document.createElement('div');
	item.className = `chat-bubble ${own ? 'chat-own' : ''} ${system ? 'chat-system' : ''}`.trim();
	item.innerHTML = `<strong>${who || 'live'}</strong><span>${text}</span><small>${new Date(created).toLocaleTimeString()}</small>`;
	box.appendChild(item);
	box.scrollTop = box.scrollHeight;
}

function scheduleChatReconnect(user) {
	clearChatReconnect();
	if (location.pathname !== '/messages') return;
	chatReconnectAttempt = Math.min(chatReconnectAttempt + 1, 6);
	const delay = 500 * Math.pow(2, chatReconnectAttempt - 1);
	setChatStatus(`Reconnecting ${chatReconnectAttempt}`, 'connecting');
	chatReconnectTimer = setTimeout(() => initChatSocket(user), delay);
}

function initChatSocket(user) {
	if (!$('#chatMessages') || !state.token) return;
	closeChatSocket();
	setChatStatus('Connecting', 'connecting');
	chatSocket = new WebSocket(getChatSocketUrl());
	chatSocket.onopen = () => { chatReconnectAttempt = 0; setChatStatus('Live', 'live'); appendChatMessage('Connected to live room', 'system'); };
	chatSocket.onmessage = (event) => {
		const raw = String(event.data || '').trim();
		const i = raw.indexOf(':');
		if (i > 0) appendChatMessage(raw.slice(i + 1).trim(), raw.slice(0, i).trim());
		else appendChatMessage(raw, 'live');
	};
	chatSocket.onerror = () => { setChatStatus('Issue', 'offline'); appendChatMessage('Connection error', 'system'); };
	chatSocket.onclose = () => { setChatStatus('Offline', 'offline'); appendChatMessage('Disconnected', 'system'); scheduleChatReconnect(user); };

	const form = $('#chatForm');
	form.onsubmit = (e) => {
		e.preventDefault();
		const input = $('#chatInput');
		const msg = String(input.value || '').trim();
		if (!msg) return;
		if (!chatSocket || chatSocket.readyState !== 1) return toast('Chat not connected', false);
		chatSocket.send(msg);
		input.value = '';
	};

	const clearBtn = $('#chatClearBtn');
	if (clearBtn) clearBtn.onclick = () => { $('#chatMessages').innerHTML = ''; };
}

function antiSpam() {
	const n = Date.now();
	if (n - state.rate.last < 5000) state.rate.count += 1;
	else state.rate.count = 1;
	state.rate.last = n;
	if (state.rate.count > 3) throw new Error('Slow down: spam protection active');
}

async function router() {
	const path = location.pathname;
	if (path !== '/messages') closeChatSocket();
	const fn = routes[path] || renderLanding;
	try { await fn(); } catch (e) { $('#view').innerHTML = '<section class="card">Error loading page</section>'; toast(e.message, false); }
	updateAuthUI();
	applyI18n();
}

function currentUser() {
	if (state.user) return state.user;
	const m = localStorage.getItem('mockUser');
	return m ? JSON.parse(m) : null;
}

async function renderLanding() { setView('#landing-template'); }

async function renderLogin() {
	setView('#login-template');
	$('#loginForm').onsubmit = async (e) => {
		e.preventDefault();
		const fd = new FormData(e.target);
		try {
			antiSpam();
			const email = String(fd.get('email') || '').trim();
			const password = String(fd.get('password') || '');
			if (firebaseReady && auth) {
				await auth.signInWithEmailAndPassword(email, password);
				state.user = { email, name: email.split('@')[0], verified: true, role: 'user' };
			} else {
				const res = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
				state.user = res.user;
				state.token = res.access_token || '';
				state.refreshToken = res.refresh_token || '';
				localStorage.setItem('authToken', state.token);
				localStorage.setItem('refreshToken', state.refreshToken);
			}
			localStorage.setItem('mockUser', JSON.stringify(state.user));
			toast('Logged in');
			navigate('/feed');
		} catch (err) {
			toast(err.message, false);
		}
	};
}

async function renderSignup() {
	setView('#signup-template');
	$('#signupForm').onsubmit = async (e) => {
		e.preventDefault();
		const fd = new FormData(e.target);
		try {
			antiSpam();
			const name = String(fd.get('name') || '').trim();
			const email = String(fd.get('email') || '').trim();
			const password = String(fd.get('password') || '');
			if (firebaseReady && auth) {
				const cred = await auth.createUserWithEmailAndPassword(email, password);
				await cred.user.sendEmailVerification();
				state.user = { name, email, verified: false, role: 'user' };
			} else {
				const res = await api('/auth/signup', { method: 'POST', body: JSON.stringify({ name, email, password }) });
				state.user = res.user;
				state.token = res.access_token || '';
				state.refreshToken = res.refresh_token || '';
				localStorage.setItem('authToken', state.token);
				localStorage.setItem('refreshToken', state.refreshToken);
			}
			localStorage.setItem('mockUser', JSON.stringify(state.user));
			toast('Registered. Verify email to unlock all features.');
			navigate('/feed');
		} catch (err) {
			toast(err.message, false);
		}
	};
}

async function renderFeed() {
	if (!currentUser()) return navigate('/login');
	setView('#feed-template');
	const stories = ['You', 'Ana', 'Leo', 'Mia', 'Noah'];
	$('#storiesBar').innerHTML = stories.map((s) => `<div class='story'><div class='tile'>${s[0]}</div><small>${s}</small></div>`).join('');
	$('#postForm').onsubmit = async (e) => {
		e.preventDefault();
		try {
			antiSpam();
			const fd = new FormData(e.target);
			const content = String(fd.get('content') || '').trim();
			if (!content) throw new Error('Write something first');
			await api('/posts', { method: 'POST', body: JSON.stringify({ content, media: String(fd.get('media') || '') }) });
			e.target.reset();
			await drawPosts();
			toast('Posted');
		} catch (err) {
			toast(err.message, false);
		}
	};
	await drawPosts();
}

async function drawPosts() {
	const box = $('#postList');
	let posts = [];
	try { const res = await api('/posts'); posts = res.posts || []; } catch (err) { toast(err.message, false); }
	if (!posts.length) posts = [{ id: 'demo', author: 'SocialSphere', content: 'Welcome to your personalized feed!', media: '', likes: 4, saved: false, comments: ['Nice!'], created: Date.now() }];
	box.innerHTML = posts.map((p) => `<article class='card post'><div class='meta'>@${p.author} · ${new Date(p.created).toLocaleString()}</div><p>${p.content}</p>${p.media ? `<a href='${p.media}' target='_blank'>Open media</a>` : ''}<div class='actions'><button class='btn like' data-id='${p.id}'>Heart ${p.likes}</button><button class='btn comment' data-id='${p.id}'>Comment ${p.comments.length}</button><button class='btn save' data-id='${p.id}' data-saved='${p.saved ? 1 : 0}'>${p.saved ? 'Saved' : 'Save'}</button><button class='btn del' data-id='${p.id}'>Delete</button></div></article>`).join('');
	box.onclick = async (e) => {
		const b = e.target.closest('button');
		if (!b) return;
		const id = b.dataset.id;
		try {
			if (b.classList.contains('like')) await api(`/posts/${id}/like`, { method: 'POST' });
			if (b.classList.contains('save')) { const isSaved = b.dataset.saved === '1'; await api(`/posts/${id}/${isSaved ? 'unsave' : 'save'}`, { method: 'POST' }); }
			if (b.classList.contains('comment')) { const c = prompt('Comment'); if (c) await api(`/posts/${id}/comment`, { method: 'POST', body: JSON.stringify({ author: currentUser().name, comment: c }) }); }
			if (b.classList.contains('del')) await api(`/posts/${id}`, { method: 'DELETE' });
			await drawPosts();
		} catch (err) { toast(err.message, false); }
	};
}

async function renderExplore() {
	if (!currentUser()) return navigate('/login');
	setView('#explore-template');
	const grid = $('#exploreGrid');
	const load = async (q = 'trending') => {
		try {
			const data = await api(`https://dummyjson.com/posts/search?q=${encodeURIComponent(q)}`);
			grid.innerHTML = (data.posts || []).slice(0, 12).map((p) => `<div class='tile'>#${p.tags?.[0] || 'trend'}</div>`).join('');
		} catch {
			grid.innerHTML = '<div class="card">Could not load explore data.</div>';
		}
	};
	$('#searchBtn').onclick = () => load($('#searchInput').value || 'news');
	load();
}

async function renderProfile() {
	if (!currentUser()) return navigate('/login');
	setView('#profile-template');
	const u = currentUser();
	let graph = { followers: [], following: [] };
	try { graph = await api('/users/me/social'); } catch {}

	$('#profileBox').innerHTML = `<p><b>${u.name}</b></p><p>${u.email}</p><p>Status: ${u.verified ? 'Verified' : 'Unverified'}</p><p>Followers: <b>${(graph.followers || []).length}</b> · Following: <b>${(graph.following || []).length}</b></p><div class='row'><input id='userSearch' type='text' placeholder='Search users by name or email' /><button class='btn' id='userSearchBtn'>Search</button></div><div id='userDirectory' class='stack mt'></div><h3 class='mt'>Followers</h3><div id='followersList' class='stack'></div><h3 class='mt'>Following</h3><div id='followingList' class='stack'></div>`;

	const drawUsers = async (search = '', offset = 0) => {
		try {
			const res = await api(`/users?query=${encodeURIComponent(search)}&limit=8&offset=${offset}`);
			const users = res.users || [];
			if (!users.length) { $('#userDirectory').innerHTML = '<div class="card">No users found.</div>'; return; }
			const next = offset + (res.limit || users.length);
			const canMore = next < (res.total || users.length);
			$('#userDirectory').innerHTML = users.map((x) => `<div class='card row between'><div><b>${x.name}</b><div class='muted'>${x.email}</div><small class='muted'>Followers ${x.followers_count} · Following ${x.following_count}</small></div><div class='row'><button class='btn followAct' data-email='${x.email}' data-following='${x.is_following ? 1 : 0}'>${x.is_following ? 'Unfollow' : 'Follow'}</button></div></div>`).join('') + (canMore ? `<button class='btn' id='usersMoreBtn' data-next='${next}'>Load More</button>` : '');
		} catch (err) {
			$('#userDirectory').innerHTML = '<div class="card">Could not load users.</div>';
			toast(err.message, false);
		}
	};

	const drawFollowersFollowing = async () => {
		try {
			const followers = await api('/users/me/followers');
			$('#followersList').innerHTML = (followers.users || []).map((x) => `<div class='card'>${x.name} <span class='muted'>${x.email}</span></div>`).join('') || '<div class="card">No followers yet.</div>';
			const following = await api('/users/me/following');
			$('#followingList').innerHTML = (following.users || []).map((x) => `<div class='card'>${x.name} <span class='muted'>${x.email}</span></div>`).join('') || '<div class="card">Not following anyone yet.</div>';
		} catch (err) {
			toast(err.message, false);
		}
	};

	$('#userSearchBtn').onclick = () => drawUsers(String($('#userSearch').value || '').trim(), 0);
	$('#userDirectory').onclick = async (e) => {
		const more = e.target.closest('#usersMoreBtn');
		if (more) return drawUsers(String($('#userSearch').value || '').trim(), Number(more.dataset.next || 0));
		const b = e.target.closest('.followAct');
		if (!b) return;
		const target = String(b.dataset.email || '').trim().toLowerCase();
		const following = b.dataset.following === '1';
		try {
			await api(`/${following ? 'unfollow' : 'follow'}/${encodeURIComponent(target)}`, { method: 'POST' });
			toast(following ? 'Unfollowed' : 'Followed');
			await renderProfile();
		} catch (err) { toast(err.message, false); }
	};

	await drawUsers('', 0);
	await drawFollowersFollowing();
}

async function renderNotifications() {
	if (!currentUser()) return navigate('/login');
	setView('#notifications-template');
	try {
		const res = await api('/notifications/me?limit=40');
		$('#notificationsList').innerHTML = (res.notifications || []).map((x) => `<div class='card'>${x.title}</div>`).join('');
	} catch (err) {
		$('#notificationsList').innerHTML = '<div class="card">Could not load notifications.</div>';
		toast(err.message, false);
	}
}

async function renderMessages() {
	if (!currentUser()) return navigate('/login');
	setView('#messages-template');
	const roomInput = $('#chatRoomInput');
	if (roomInput) roomInput.value = state.chatRoom || 'global';
	const joinRoomBtn = $('#joinRoomBtn');
	if (joinRoomBtn) {
		joinRoomBtn.onclick = async () => {
			state.chatRoom = String($('#chatRoomInput').value || 'global').trim() || 'global';
			localStorage.setItem('chatRoom', state.chatRoom);
			await renderMessages();
		};
	}
	try {
		const res = await api('/messages/me');
		$('#dmList').innerHTML = (res.messages || []).map((x) => `<div class='card'>${x.from_user}: ${x.text}</div>`).join('');
	} catch (err) {
		$('#dmList').innerHTML = '<div class="card">Could not load messages.</div>';
		toast(err.message, false);
	}

	try {
		const history = await api(`/chat/messages/${encodeURIComponent(state.chatRoom)}?limit=50`);
		$('#chatMessages').innerHTML = '';
		(history.messages || []).forEach((x) => appendChatMessage(x.text, x.from_user, x.created));
	} catch (err) {
		appendChatMessage('Could not load previous room messages', 'system');
	}
	appendChatMessage(`Room: ${state.chatRoom}`, 'system');
	initChatSocket(currentUser());
}

async function renderAdmin() {
	if (!currentUser() || currentUser().role !== 'admin') return navigate('/feed');
	setView('#admin-template');
	$('#flaggedBtn').onclick = async () => {
		try {
			const data = await api('/admin/flagged');
			$('#moderationList').innerHTML = (data || []).map((x) => `<div class='card row between'><span>${x}</span><span><button class='btn'>Approve</button> <button class='btn'>Remove</button></span></div>`).join('');
		} catch (err) {
			toast(err.message, false);
		}
	};

	$('#auditBtn').onclick = async () => {
		try {
			const data = await api('/admin/audit-logs?limit=80');
			$('#auditList').innerHTML = (data || []).map((x) => `<div class='card'><b>${x.action || 'action'}</b> · ${x.actor || 'unknown'}${x.target ? ` -> ${x.target}` : ''}<div class='muted'>${new Date(Number(x.created || Date.now())).toLocaleString()}</div></div>`).join('') || '<div class="card">No audit logs found.</div>';
		} catch (err) {
			toast(err.message, false);
		}
	};
}

(function init() {
	state.user = currentUser();
	$('#year').textContent = new Date().getFullYear();
	applyTheme();
	updateAuthUI();
	router();
})();