export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const id = getRouterParam(event, 'id')
  const target = `${config.apiUrl}/status/${id}`
  
  return proxyRequest(event, target)
})
