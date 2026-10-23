// Block Catch leaderboard relay. dreamlo's free tier is HTTP only, which browsers refuse, so the game talks
// to this over HTTPS instead. It also keeps dreamlo's private (score-adding) code out of the game's files.
//   GET /add/<name>/<score>         adds a score
//   GET /add/<name>/<score>/<skin>  adds a score with the color the player wore (kept in dreamlo's text field)
//   GET /json/<count>               the top scores, as dreamlo's JSON
//   GET /delete/<name>              removes a score; needs the X-Admin-Key header to match the ADMIN_KEY secret
//                                   (run delete_score.py rather than calling this by hand)
async function isAdmin(request, env) {
  const given = request.headers.get("X-Admin-Key") || "";
  if (!env.ADMIN_KEY || !given) return false;
  // compare hashes, so the check takes the same time however much of the key is right
  const hash = async (s) => new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)));
  const [a, b] = await Promise.all([hash(given), hash(env.ADMIN_KEY)]);
  return crypto.subtle.timingSafeEqual(a, b);
}

export default {
  async fetch(request, env) {
    const headers = {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
      "Content-Type": "text/plain; charset=utf-8",
    };
    const parts = new URL(request.url).pathname.split("/").filter(Boolean);
    let target = null;
    if (parts[0] === "add" && parts.length === 3 && parts[1].length <= 60 && /^\d{1,9}$/.test(parts[2])) {
      target = `${env.DREAMLO_PRIVATE}/add/${parts[1]}/${parts[2]}`;
    } else if (parts[0] === "add" && parts.length === 4 && parts[1].length <= 60 && /^\d{1,9}$/.test(parts[2])
               && /^\d{1,3}$/.test(parts[3])) {
      target = `${env.DREAMLO_PRIVATE}/add/${parts[1]}/${parts[2]}/0/${parts[3]}`;
    } else if (parts[0] === "json" && parts.length === 2 && /^\d{1,3}$/.test(parts[1])) {
      target = `${env.DREAMLO_PUBLIC}/json/${parts[1]}`;
    } else if (parts[0] === "delete" && parts.length === 2 && parts[1].length <= 60) {
      if (!(await isAdmin(request, env))) {
        return new Response("wrong admin key", { status: 403, headers });
      }
      target = `${env.DREAMLO_PRIVATE}/delete/${parts[1]}`;
    }
    if (!target) {
      return new Response("not found", { status: 404, headers });
    }
    const reply = await fetch("http://dreamlo.com/lb/" + target, { headers: { "User-Agent": "BlockCatchRelay" } });
    return new Response(await reply.text(), { status: reply.status, headers });
  },
};
