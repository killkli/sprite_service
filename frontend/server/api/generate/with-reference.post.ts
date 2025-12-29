/**
 * BFF Proxy for /generate/with-reference endpoint
 * 代理參考圖片生成請求到內部 API (Image-to-Image)
 */
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const target = `${config.apiUrl}/generate/with-reference`

  // Use proxyRequest to forward the request including multipart form data
  return proxyRequest(event, target, {
    fetchOptions: {
      method: 'POST',
    }
  })
})
