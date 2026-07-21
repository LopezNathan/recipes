import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// Static output (default) for Cloudflare Pages. No server, no adapter.
export default defineConfig({
  site: 'https://recipes-astro.pages.dev',
  integrations: [preact()],
});
