/**
 * BFF Proxy for /generate endpoint
 * 代理文字生圖請求到內部 API
 */
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)

  try {
    const response = await $fetch(`${config.apiUrl}/generate`, {
      method: 'POST',
      body: body,
    })

    return response
  } catch (error: any) {
    // Forward error status from backend
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Generation failed',
      data: error.data
    })
  }
})
