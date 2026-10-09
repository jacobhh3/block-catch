// Block Catch leaderboard relay. dreamlo's free tier is HTTP only, which browsers refuse, so the game talks
// to this over HTTPS instead. It also keeps dreamlo's private (score-adding) code out of the game's files.
//   GET /add/<name>/<score>  adds a score
//   GET /json/<count>        the top scores, as dreamlo's JSON
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
    } else if (parts[0] === "json" && parts.length === 2 && /^\d{1,3}$/.test(parts[1])) {
      target = `${env.DREAMLO_PUBLIC}/json/${parts[1]}`;
    }
    if (!target) {
      return new Response("not found", { status: 404, headers });
    }
    const reply = await fetch("http://dreamlo.com/lb/" + target, { headers: { "User-Agent": "BlockCatchRelay" } });
    return new Response(await reply.text(), { status: reply.status, headers });
  },
};
