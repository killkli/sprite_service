export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const target = `${config.apiUrl}/process/grid`

  // Use sendProxy to forward the request including multipart data
  return proxyRequest(event, target, {
    fetchOptions: {
      method: 'POST',
    }
  })
})
