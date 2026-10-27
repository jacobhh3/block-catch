// Block Catch leaderboard relay. dreamlo's free tier is HTTP only, which browsers refuse, so the game talks
// to this over HTTPS instead. It also keeps dreamlo's private (score-adding) code out of the game's files.
//   GET /add/<name>/<score>         adds a score
//   GET /add/<name>/<score>/<skin>  adds a score with the color the player wore (kept in dreamlo's text field)
//   GET /add/<name>/<score>/<skin>/<hat>  ...and the hat, as its number + 1 (0: none), kept in dreamlo's seconds field
//   GET /json/<count>               the top scores, as dreamlo's JSON, each in the color and hat its player last
//                                   wore (dreamlo only keeps them with a new best, so they're also kept in STORE "looks")
//   GET /week/<count>               this week's top scores (weeks start Monday 12am Eastern), as JSON
//   GET /daily/add/<name>/<score>/<skin>[/<hat>]  a Daily Challenge score; only a player's first of the day counts
//   GET /daily/<count>              today's Daily Challenge board, and yesterday's top 10 (its #1 wears the crown)
//   GET /delete/<name>              removes a score; needs the X-Admin-Key header to match the ADMIN_KEY secret
//                                   (run delete_score.py rather than calling this by hand)
//   GET /admin/set/<name>/<score>/<skin>/<hat>  puts a score on the board exactly as given (replacing, even with a
//                                   lower score), with that color and hat (+1, 0: none); also on this week's board if
//                                   the name is there. Needs X-Admin-Key (the Leaderboard Manager app uses it)
//   GET /update                     the update countdown: {"at": when it ends (ms since 1970, 0: none), "start": when
//                                   it was set, "now": the time}
//   GET /update/set/<minutes>       starts the countdown (0 cancels it); needs X-Admin-Key (run update_timer.py)
//   POST /sync                      starts a cross save from a progress update (see mergeSync); replies with its code
//   POST /sync/<code>               adds a progress update to a cross save; replies with the combined save
// Weekly scores and cross saves are kept in the STORE key-value namespace (see wrangler.toml).
const CODE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"; // no 0/O, 1/I/L to mix up when typing a code in
const DAY = 24 * 60 * 60;

async function isAdmin(request, env) {
  const given = request.headers.get("X-Admin-Key") || "";
  if (!env.ADMIN_KEY || !given) return false;
  // compare hashes, so the check takes the same time however much of the key is right
  const hash = async (s) => new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)));
  const [a, b] = await Promise.all([hash(given), hash(env.ADMIN_KEY)]);
  return crypto.subtle.timingSafeEqual(a, b);
}

// ---------- dates (boards turn over at midnight Eastern) ----------
function easternDate(now) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now).map((x) => [x.type, x.value]));
  return new Date(Date.UTC(+p.year, +p.month - 1, +p.day));
}

export function easternDay(now = new Date(), back = 0) {
  // today's date in Eastern time (or back days before it), as YYYY-MM-DD
  const day = easternDate(now);
  day.setUTCDate(day.getUTCDate() - back);
  return day.toISOString().slice(0, 10);
}

// ---------- weekly board ----------
export function weekStart(now = new Date()) {
  // the Monday (in Eastern time) the current week began on, as YYYY-MM-DD
  const day = easternDate(now);
  day.setUTCDate(day.getUTCDate() - (day.getUTCDay() + 6) % 7);
  return day.toISOString().slice(0, 10);
}

async function recordWeek(env, key, score, skin, hat = 0) {
  // each name keeps its best score of the week
  const wk = "week:" + weekStart();
  const board = (await env.STORE.get(wk, "json")) || {};
  if (!board[key] || score > board[key].score) {
    board[key] = { score, skin, hat };
    await env.STORE.put(wk, JSON.stringify(board), { expirationTtl: 21 * DAY });
  }
}

async function topOfWeek(env, count) {
  const week = weekStart();
  const [board, looks] = await Promise.all([env.STORE.get("week:" + week, "json"), env.STORE.get("looks", "json")]);
  const entries = Object.entries(board || {}).map(([name, e]) => {
    const look = (looks || {})[name];
    return { name, score: e.score, skin: look ? look.skin : e.skin, hat: look ? look.hat : e.hat || 0 };
  }).sort((a, b) => b.score - a.score).slice(0, count);
  return { week, entries };
}

// ---------- the color and hat each player last wore ----------
async function recordLook(env, key, skin, hat) {
  // every run counts, not just a new best, so the boards show what a player wears now
  const looks = (await env.STORE.get("looks", "json")) || {};
  const was = looks[key];
  if (!was || was.skin !== skin || was.hat !== hat) {
    looks[key] = { skin, hat };
    await env.STORE.put("looks", JSON.stringify(looks));
  }
}

async function dressBoard(env, text) {
  // dreamlo's JSON, with each entry's text (color) and seconds (hat + 1) set to the player's latest look
  const looks = await env.STORE.get("looks", "json");
  if (!looks) return text;
  try {
    const data = JSON.parse(text);
    const board = data.dreamlo && data.dreamlo.leaderboard;
    let rows = board && board.entry;
    if (!rows) return text;
    for (const r of Array.isArray(rows) ? rows : [rows]) {
      const look = looks[r.name];
      if (look) { r.text = String(look.skin); r.seconds = String(look.hat); }
    }
    return JSON.stringify(data);
  } catch (e) {
    return text;
  }
}

// ---------- Daily Challenge ----------
const playerOf = (key) => key.slice(key.lastIndexOf("_") + 1); // names are NAME_<player id>

export async function recordDaily(env, key, score, skin, now = new Date(), hat = 0) {
  // one try a day: a player's first score of the day stands, whatever name or device they use next
  const dk = "day:" + easternDay(now);
  const board = (await env.STORE.get(dk, "json")) || {};
  if (Object.keys(board).some((k) => playerOf(k) === playerOf(key))) return false;
  board[key] = { score, skin, hat };
  await env.STORE.put(dk, JSON.stringify(board), { expirationTtl: 3 * DAY });
  return true;
}

async function dailyBoard(env, count, now = new Date()) {
  const top = async (day, n) => Object.entries((await env.STORE.get("day:" + day, "json")) || {})
    .map(([name, e]) => ({ name, score: e.score, skin: e.skin, hat: e.hat || 0 })).sort((a, b) => b.score - a.score).slice(0, n);
  const day = easternDay(now), yesterday = easternDay(now, 1);
  return { day, entries: await top(day, count), yesterday: { day: yesterday, entries: await top(yesterday, 10) } };
}

// ---------- cross save ----------
// A progress update from a device: what it gained since it last synced. "add" totals are added on, "max" keeps
// the larger, "union" lists are merged (unlocks, days played). device + req mark the update, so a retry of one
// that already got through isn't counted twice.
export function mergeSync(save, update) {
  save.add ||= {};
  save.max ||= {};
  save.union ||= {};
  save.applied ||= {};
  const device = typeof update.device === "string" ? update.device.slice(0, 16) : "";
  if (device && save.applied[device] === update.req) return save;
  for (const [k, v] of Object.entries(update.add || {})) {
    if (Number.isFinite(v) && v > 0) save.add[k] = (save.add[k] || 0) + v;
  }
  for (const [k, v] of Object.entries(update.max || {})) {
    if (Number.isFinite(v)) save.max[k] = Math.max(save.max[k] ?? v, v);
  }
  for (const [k, v] of Object.entries(update.union || {})) {
    if (Array.isArray(v)) save.union[k] = [...new Set([...(save.union[k] || []), ...v])].slice(0, 5000);
  }
  if (!save.player_id && typeof update.player_id === "string") save.player_id = update.player_id.slice(0, 8);
  if (typeof update.name === "string" && update.name) save.name = update.name.slice(0, 20);
  if (device) save.applied[device] = update.req;
  return save;
}

function newCode() {
  return Array.from(crypto.getRandomValues(new Uint8Array(8)), (b) => CODE_CHARS[b % CODE_CHARS.length]).join("");
}

async function sync(request, env, code, headers) {
  const body = await request.text();
  if (body.length > 64 * 1024) return new Response("too big", { status: 413, headers });
  let update;
  try {
    update = JSON.parse(body);
  } catch {
    return new Response("bad save", { status: 400, headers });
  }
  let save = {};
  if (code) {
    save = await env.STORE.get("sync:" + code, "json");
    if (!save) return new Response("no such code", { status: 404, headers });
  } else {
    do code = newCode(); while (await env.STORE.get("sync:" + code));
  }
  save = mergeSync(save, update);
  save.code = code;
  // kept a year from its last use
  await env.STORE.put("sync:" + code, JSON.stringify(save), { expirationTtl: 365 * DAY });
  const { applied, ...reply } = save;
  return new Response(JSON.stringify(reply), { headers: { ...headers, "Content-Type": "application/json" } });
}

export default {
  async fetch(request, env) {
    const headers = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Cache-Control": "no-store",
      "Content-Type": "text/plain; charset=utf-8",
    };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    const parts = new URL(request.url).pathname.split("/").filter(Boolean);

    if (parts[0] === "sync" && request.method === "POST" && env.STORE) {
      if (parts.length === 1) return sync(request, env, null, headers);
      if (parts.length === 2 && new RegExp(`^[${CODE_CHARS}]{8}$`).test(parts[1])) {
        return sync(request, env, parts[1], headers);
      }
      return new Response("bad code", { status: 400, headers });
    }
    if (parts[0] === "daily" && env.STORE) {
      if (parts[1] === "add" && (parts.length === 5 || parts.length === 6) && parts[2].length <= 60
          && /^\d{1,9}$/.test(parts[3]) && /^\d{1,3}$/.test(parts[4]) && (parts.length === 5 || /^\d{1,3}$/.test(parts[5]))) {
        const ok = await recordDaily(env, decodeURIComponent(parts[2]), +parts[3], +parts[4], new Date(), +(parts[5] || 0));
        return new Response(ok ? "OK" : "ALREADY PLAYED TODAY", { headers });
      }
      if (parts.length === 2 && /^\d{1,3}$/.test(parts[1])) {
        const board = await dailyBoard(env, Math.min(100, +parts[1]));
        return new Response(JSON.stringify(board), { headers: { ...headers, "Content-Type": "application/json" } });
      }
    }
    if (parts[0] === "admin" && parts[1] === "set" && parts.length === 6 && parts[2].length <= 60
        && /^\d{1,9}$/.test(parts[3]) && /^\d{1,3}$/.test(parts[4]) && /^\d{1,3}$/.test(parts[5]) && env.STORE) {
      if (!(await isAdmin(request, env))) return new Response("wrong admin key", { status: 403, headers });
      const key = decodeURIComponent(parts[2]), score = +parts[3], skin = +parts[4], hat = +parts[5];
      const dreamlo = (path) => fetch("http://dreamlo.com/lb/" + path, { headers: { "User-Agent": "BlockCatchRelay" } })
        .then((r) => r.text());
      await dreamlo(`${env.DREAMLO_PRIVATE}/delete/${parts[2]}`);  // dreamlo only raises a score, so start fresh
      const text = await dreamlo(`${env.DREAMLO_PRIVATE}/add/${parts[2]}/${score}/${hat}/${skin}`);
      if (!text.startsWith("OK")) return new Response(text, { status: 502, headers });
      await recordLook(env, key, skin, hat);
      const wk = "week:" + weekStart();
      const board = (await env.STORE.get(wk, "json")) || {};
      if (board[key]) {
        board[key] = { score, skin, hat };
        await env.STORE.put(wk, JSON.stringify(board), { expirationTtl: 21 * DAY });
      }
      return new Response("OK", { headers });
    }
    if (parts[0] === "update" && env.STORE) {
      const json = { ...headers, "Content-Type": "application/json" };
      if (parts.length === 1) {
        const t = (await env.STORE.get("update", "json")) || { at: 0, start: 0 };
        return new Response(JSON.stringify({ ...t, now: Date.now() }), { headers: json });
      }
      if (parts.length === 3 && parts[1] === "set" && /^\d{1,4}$/.test(parts[2])) {
        if (!(await isAdmin(request, env))) return new Response("wrong admin key", { status: 403, headers });
        const now = Date.now();
        const t = { at: +parts[2] ? now + +parts[2] * 60000 : 0, start: now };  // games built after start skip it
        await env.STORE.put("update", JSON.stringify(t), { expirationTtl: 2 * DAY });
        return new Response(JSON.stringify({ ...t, now }), { headers: json });
      }
    }
    if (parts[0] === "week" && parts.length === 2 && /^\d{1,3}$/.test(parts[1]) && env.STORE) {
      const top = await topOfWeek(env, Math.min(100, +parts[1]));
      return new Response(JSON.stringify(top), { headers: { ...headers, "Content-Type": "application/json" } });
    }

    let target = null, adding = null;
    if (parts[0] === "add" && parts.length === 3 && parts[1].length <= 60 && /^\d{1,9}$/.test(parts[2])) {
      target = `${env.DREAMLO_PRIVATE}/add/${parts[1]}/${parts[2]}`;
      adding = { key: decodeURIComponent(parts[1]), score: +parts[2], skin: null };
    } else if (parts[0] === "add" && parts.length === 4 && parts[1].length <= 60 && /^\d{1,9}$/.test(parts[2])
               && /^\d{1,3}$/.test(parts[3])) {
      target = `${env.DREAMLO_PRIVATE}/add/${parts[1]}/${parts[2]}/0/${parts[3]}`;
      adding = { key: decodeURIComponent(parts[1]), score: +parts[2], skin: +parts[3], hat: 0 };
    } else if (parts[0] === "add" && parts.length === 5 && parts[1].length <= 60 && /^\d{1,9}$/.test(parts[2])
               && /^\d{1,3}$/.test(parts[3]) && /^\d{1,3}$/.test(parts[4])) {
      target = `${env.DREAMLO_PRIVATE}/add/${parts[1]}/${parts[2]}/${+parts[4]}/${parts[3]}`;
      adding = { key: decodeURIComponent(parts[1]), score: +parts[2], skin: +parts[3], hat: +parts[4] };
    } else if (parts[0] === "json" && parts.length === 2 && /^\d{1,3}$/.test(parts[1])) {
      target = `${env.DREAMLO_PUBLIC}/json/${parts[1]}`;
    } else if (parts[0] === "delete" && parts.length === 2 && parts[1].length <= 60) {
      if (!(await isAdmin(request, env))) {
        return new Response("wrong admin key", { status: 403, headers });
      }
      target = `${env.DREAMLO_PRIVATE}/delete/${parts[1]}`;
      if (env.STORE) {  // off this week's board too
        const wk = "week:" + weekStart();
        const board = (await env.STORE.get(wk, "json")) || {};
        if (delete board[decodeURIComponent(parts[1])]) await env.STORE.put(wk, JSON.stringify(board), { expirationTtl: 21 * DAY });
        const dk = "day:" + easternDay();
        const today = (await env.STORE.get(dk, "json")) || {};
        if (delete today[decodeURIComponent(parts[1])]) await env.STORE.put(dk, JSON.stringify(today), { expirationTtl: 3 * DAY });
      }
    }
    if (!target) {
      return new Response("not found", { status: 404, headers });
    }
    const reply = await fetch("http://dreamlo.com/lb/" + target, { headers: { "User-Agent": "BlockCatchRelay" } });
    const text = await reply.text();
    if (adding && env.STORE && text.startsWith("OK")) {
      await recordWeek(env, adding.key, adding.score, adding.skin, adding.hat || 0);
      if (adding.skin !== null) await recordLook(env, adding.key, adding.skin, adding.hat || 0);
    }
    if (parts[0] === "json" && env.STORE && reply.ok) {
      return new Response(await dressBoard(env, text), { status: reply.status, headers });
    }
    return new Response(text, { status: reply.status, headers });
  },
};
