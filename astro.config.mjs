// @ts-check

import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { defineConfig, fontProviders } from 'astro/config';
import remarkCjkFriendly from 'remark-cjk-friendly';
import rehypeEditorial from './src/lib/rehype-editorial.mjs';

// https://astro.build/config
export default defineConfig({
	site: 'https://seoul.jworld.dev',
	integrations: [mdx(), sitemap()],
	markdown: {
		remarkPlugins: [remarkCjkFriendly],
		rehypePlugins: [rehypeEditorial],
	},
	fonts: [
		{
			provider: fontProviders.google(),
			name: 'Noto Sans JP',
			cssVariable: '--font-sans',
			weights: [400, 500, 700],
			styles: ['normal'],
			subsets: ['japanese', 'latin'],
			fallbacks: ['Hiragino Sans', 'Yu Gothic', 'sans-serif'],
		},
		{
			provider: fontProviders.google(),
			name: 'Zen Old Mincho',
			cssVariable: '--font-serif',
			weights: [500, 700],
			styles: ['normal'],
			subsets: ['japanese', 'latin'],
			fallbacks: ['Hiragino Mincho ProN', 'Yu Mincho', 'serif'],
		},
	],
});
