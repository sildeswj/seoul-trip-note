// 記事本文を雑誌風に整える rehype プラグイン。
// 1) 「結論」「要点」を含む見出しと直後のリストを .summary-box で囲む
// 2) table を横スクロールできる .table-wrap で囲む
// 3) 本文冒頭（最初の見出しより前）の hr を取り除く
const text = (n) => (n.type === 'text' ? n.value : (n.children || []).map(text).join(''));
const isHeading = (n) => n.type === 'element' && /^h[2-4]$/.test(n.tagName);

// 日本語の句読点のそばで ** が太字にならず残ったものを <strong> に直す
function fixStars(node) {
	if (!node.children) return;
	const next = [];
	for (const c of node.children) {
		if (c.type === 'text' && c.value.includes('**')) {
			const parts = c.value.split(/\*\*([^*]+?)\*\*/);
			parts.forEach((v, i) => {
				if (!v) return;
				next.push(i % 2 ? { type: 'element', tagName: 'strong', properties: {}, children: [{ type: 'text', value: v }] } : { type: 'text', value: v });
			});
		} else {
			if (c.type === 'element' && c.tagName !== 'code' && c.tagName !== 'pre') fixStars(c);
			next.push(c);
		}
	}
	node.children = next;
}

export default function rehypeEditorial() {
	return (tree) => {
		const out = [];
		const kids = tree.children;
		for (let i = 0; i < kids.length; i++) {
			const n = kids[i];
			if (isHeading(n) && /結論|要点|まとめボックス|わかること/.test(text(n))) {
				const box = { type: 'element', tagName: 'aside', properties: { className: ['summary-box'] }, children: [{ ...n, tagName: 'p', properties: { className: ['summary-title'] } }] };
				let j = i + 1;
				while (j < kids.length && !isHeading(kids[j]) && !(kids[j].type === 'element' && kids[j].tagName === 'hr')) {
					box.children.push(kids[j]);
					j++;
				}
				out.push(box);
				i = j - 1;
				continue;
			}
			if (n.type === 'element' && n.tagName === 'table') {
				out.push({ type: 'element', tagName: 'div', properties: { className: ['table-wrap'] }, children: [n] });
				continue;
			}
			out.push(n);
		}
		// 最初の見出しより前の hr と、h2 の直前の hr は消す（h2 に区切り線があるため）
		const els = out.filter((n) => n.type === 'element');
		const firstH = els.findIndex(isHeading);
		tree.children = out.filter((n) => {
			if (!(n.type === 'element' && n.tagName === 'hr')) return true;
			const i = els.indexOf(n);
			const nextEl = els[i + 1];
			return !(firstH === -1 || i < firstH || (nextEl && nextEl.tagName === 'h2'));
		});
		fixStars(tree);
	};
}
