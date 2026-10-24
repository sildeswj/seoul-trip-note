// Agoda Partners hotel links (approval pending since 2026-10-24).
//
// While AGODA_CID is empty, every Agoda placement renders NOTHING:
//   - `<div data-agoda="myeongdong"></div>` markers inside posts (src/lib/rehype-agoda.mjs)
//   - the hotel box after posts that list `agoda:` areas in frontmatter (src/components/AgodaBox.astro)
//
// After approval:
//   1. Put the CID from Agoda Partners (Tools > Text Links) in AGODA_CID.
//   2. Check AGODA_DEFAULT_URL against the link Agoda's tool actually gives you.
//   3. Optional: paste an area search link from Agoda's link tool into AREAS[x].url
//      so that area's links open a filtered hotel list instead of the generic search.
//   4. Clear Astro's content cache (`rm -rf node_modules/.astro .astro`; rendered Markdown is cached and
//      would keep the old, empty markers), then build and deploy. All markers and boxes turn on at once.

export const AGODA_CID = '';

/** Generic Agoda search link (template from the Agoda Partners text-link page; confirm after approval). */
export const AGODA_DEFAULT_URL = AGODA_CID ? `https://www.agoda.com/partners/partnersearch.aspx?pcs=1&cid=${AGODA_CID}` : '';

/** Area keys used by posts. `url` stays empty until a real area link is copied from Agoda's link tool. */
export const AREAS = {
	seoul: { label: 'ソウル', url: '' },
	myeongdong: { label: '明洞', url: '' },
	hongdae: { label: '弘大・延南洞', url: '' },
	dongdaemun: { label: '東大門', url: '' },
	gangnam: { label: '江南', url: '' },
	jongno: { label: '鍾路・仁寺洞', url: '' },
	seoulstation: { label: 'ソウル駅', url: '' },
	incheon: { label: '仁川空港周辺', url: '' },
};

export const agodaEnabled = () => AGODA_CID !== '';

/** Link for an area, or null while the CID is empty (callers then render nothing). */
export function agodaUrl(area) {
	if (!agodaEnabled()) return null;
	return AREAS[area]?.url || AGODA_DEFAULT_URL;
}

export function agodaLabel(area) {
	return AREAS[area]?.label ?? 'ソウル';
}
