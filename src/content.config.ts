import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
	// Load Markdown and MDX files in the `src/content/blog/` directory.
	loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
	// Type-check frontmatter using a schema
	schema: ({ image }) =>
		z.object({
			title: z.string(),
			description: z.string(),
			// Transform string to Date object
			pubDate: z.coerce.date(),
			updatedDate: z.coerce.date().optional(),
			heroImage: z.optional(image()),
			heroAlt: z.string().optional(),
			// AI生成画像なら true（記事ページにキャプションを表示）
			heroAi: z.boolean().optional(),
			// アフィリエイトリンクを含むなら true（記事冒頭に PR 表記。ステマ規制対応）
			pr: z.boolean().optional(),
			// 任意: cosme / shopping / cafe / clinic / travel（未指定ならタイトルから推定）
			category: z.string().optional(),
			// 任意: Agoda のホテル検索ボックスを出すエリア（src/lib/agoda.mjs の AREAS のキー）。CID 設定までは何も表示しない
			agoda: z.array(z.string()).optional(),
		}),
});

export const collections = { blog };
