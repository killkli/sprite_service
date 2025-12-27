export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const id = getRouterParam(event, 'id')
  const target = `${config.apiUrl}/download/${id}`
  
  return proxyRequest(event, target)
})
