// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: ['@nuxt/ui', '@nuxtjs/i18n'],

  // i18n configuration
  i18n: {
    locales: [
      { code: 'zh-TW', name: '繁體中文', file: 'zh-TW.json' },
      { code: 'en', name: 'English', file: 'en.json' }
    ],
    defaultLocale: 'zh-TW',
    strategy: 'no_prefix',
    bundle: {
      optimizeTranslationDirective: false
    },
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_locale',
      fallbackLocale: 'zh-TW'
    }
  },

  // Runtime config for server-side environment variables
  runtimeConfig: {
    // The internal URL for the Python API (only accessible from server-side)
    // Docker service name is 'api', internal port is 8000
    apiUrl: 'http://api:8000',

    // Public keys that are exposed to the client
    public: {}
  },

  compatibilityDate: '2025-01-01'
})
