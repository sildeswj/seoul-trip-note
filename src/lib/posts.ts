import { type CollectionEntry, getCollection } from 'astro:content';

export type Post = CollectionEntry<'blog'>;

export type Category = { slug: string; label: string; en: string; tone: string; ink: string };

export const CATEGORIES: Category[] = [
	{ slug: 'cosme', label: 'コスメ・スキンケア', en: 'BEAUTY', tone: '#F3E3DF', ink: '#8A3B46' },
	{ slug: 'shopping', label: 'お買い物・免税', en: 'SHOPPING', tone: '#E6E9DF', ink: '#4D5B3A' },
	{ slug: 'cafe', label: 'カフェ・グルメ', en: 'CAFE & FOOD', tone: '#EEE4D6', ink: '#7A5530' },
	{ slug: 'clinic', label: '美容クリニック', en: 'CLINIC', tone: '#E4E6EE', ink: '#3E4A72' },
	{ slug: 'travel', label: '旅のTIPS', en: 'TRAVEL TIPS', tone: '#DFE8EA', ink: '#2F5B63' },
];

const RULES: [RegExp, string][] = [
	[/コスメ|スキンケア|トナー|美容液|リードル|クリーム|パッド|メイク|日焼け止め/, 'cosme'],
	[/クリニック|皮膚科|レーザー|施術/, 'clinic'],
	[/カフェ|グルメ|ベーカリー|レストラン|聖水|漢南/, 'cafe'],
	[/免税|還付|タックス|セール|お買い物|お土産/, 'shopping'],
	[/交通|地下鉄|WOWPASS|SIM|空港|ホテル|両替/, 'travel'],
	[/オリヤン|オリーブヤング|ダイソー/, 'shopping'],
];

/** タイトルと説明からカテゴリを推定（自動投稿のフロントマターは変えずに済むように） */
export function categoryOf(post: Post): Category {
	const fm = (post.data as { category?: string }).category;
	if (fm) {
		const c = CATEGORIES.find((x) => x.slug === fm);
		if (c) return c;
	}
	const s = `${post.data.title} ${post.id}`;
	for (const [re, slug] of RULES) if (re.test(s)) return CATEGORIES.find((c) => c.slug === slug)!;
	return CATEGORIES[4];
}

export async function getPosts(): Promise<Post[]> {
	return (await getCollection('blog')).sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf());
}

/** 日本語は1分あたり約500字として読了時間を出す */
export function readingMinutes(post: Post): number {
	const body = (post.body ?? '').replace(/[#>*|\-:`\s]/g, '');
	return Math.max(1, Math.round(body.length / 500));
}

/** heroImage が Astro のテンプレ画像ならタイポグラフィの表紙を使う */
export const isPlaceholder = (post: Post) => !post.data.heroImage || /blog-placeholder/.test(post.data.heroImage.src);

/** タイトルの【】を外した短い見出し */
export function shortTitle(title: string): string {
	return title.replace(/^【[^】]*】\s*/, '').replace(/[！!]+$/, '');
}

export function related(all: Post[], post: Post, n = 3): Post[] {
	const cat = categoryOf(post).slug;
	const same = all.filter((p) => p.id !== post.id && categoryOf(p).slug === cat);
	const rest = all.filter((p) => p.id !== post.id && categoryOf(p).slug !== cat);
	return [...same, ...rest].slice(0, n);
}

export function fmtDate(d: Date): string {
	return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

/** 記事末尾のFAQセクション（### 見出し または **Q1:...**）からQ&Aを抽出してJSON-LD用に返す */
export function extractFaqs(post: Post): { question: string; answer: string }[] {
	const body = post.body ?? '';
	const m = body.match(/(?:^|\n)#{2,3}\s*[^\n]*(?:FAQ|よくある質問|Preguntas\s+frecuentes)[^\n]*\n([\s\S]*)/i);
	const scope = (m ? m[1] : body).split(/\n##\s+/)[0];
	const faqs: { question: string; answer: string }[] = [];
	const h3Re = /(?:^|\n)###\s+([^\n]+)\n+([^\n#]+(?:\n(?!###|##|---)[^\n#]+)*)/g;
	for (const match of scope.matchAll(h3Re)) {
		const rawQ = match[1].trim();
		const qClean = rawQ.replace(/^(?:Q\d*|\d+)[:.．\s]+/i, '').replace(/^\*+|\*+$/g, '').trim();
		const aClean = match[2]
			.trim()
			.replace(/^(?:A\d*)[:.．\s]+/i, '')
			.replace(/\*\*([^*]+)\*\*/g, '$1')
			.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
			.trim();
		if ((qClean.includes('?') || qClean.includes('？') || /^Q/i.test(rawQ)) && aClean.length > 15) {
			faqs.push({ question: qClean, answer: aClean });
		}
	}
	if (faqs.length === 0) {
		const boldRe = /\*\*Q\d*[:.．\s]*([^\n*]+)\*\*\s*\n+(?:A\d*[:.．\s]*)?([^\n]+)/gi;
		for (const match of scope.matchAll(boldRe)) {
			const qClean = match[1].trim();
			const aClean = match[2]
				.trim()
				.replace(/^(?:\*\*A\d*[:.．\s]*\*\*|A\d*[:.．\s]+)/i, '')
				.replace(/\*\*([^*]+)\*\*/g, '$1')
				.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
				.trim();
			if (aClean.length > 15) {
				faqs.push({ question: qClean, answer: aClean });
			}
		}
	}
	return faqs;
}

