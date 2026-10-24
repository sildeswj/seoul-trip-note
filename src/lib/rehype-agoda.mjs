// Replaces `<div data-agoda="area"></div>` markers in posts with an Agoda hotel link.
// While AGODA_CID is empty (src/lib/agoda.mjs) the marker is removed, so nothing renders.
import { agodaLabel, agodaUrl } from './agoda.mjs';

function walk(node) {
	if (!node.children) return;
	const next = [];
	for (const c of node.children) {
		// Astro keeps inline HTML from .md as `raw` nodes; MDX/parsed HTML gives elements
		const area =
			c.type === 'element'
				? c.properties?.dataAgoda
				: c.type === 'raw'
					? c.value.match(/^\s*<div data-agoda="([\w-]+)"\s*><\/div>\s*$/)?.[1]
					: undefined;
		if (area === undefined) {
			walk(c);
			next.push(c);
			continue;
		}
		const href = agodaUrl(String(area));
		if (!href) continue;
		next.push({
			type: 'element',
			tagName: 'p',
			properties: { className: ['agoda-link'] },
			children: [
				{
					type: 'element',
					tagName: 'a',
					properties: { href, target: '_blank', rel: ['sponsored', 'noopener'] },
					children: [{ type: 'text', value: `${agodaLabel(String(area))}のホテルをAgodaで探す →` }],
				},
				{ type: 'element', tagName: 'span', properties: {}, children: [{ type: 'text', value: 'PR' }] },
			],
		});
	}
	node.children = next;
}

export default function rehypeAgoda() {
	return (tree) => walk(tree);
}
