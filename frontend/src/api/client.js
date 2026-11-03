import axios from 'axios'

const api = axios.create({ baseURL: '' })

export const startAnalysis = (file, batch = false) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post(`/analyze${batch ? '?batch=true' : ''}`, fd)
}

export const getResult = (incidentNumber) =>
  api.get(`/result/${incidentNumber}`)

export const getSavedResult = (incidentNumber) =>
  api.get(`/result/saved/${incidentNumber}`)

export const getBatchHistory = () =>
  api.get('/batch')

export const getPending = () =>
  api.get('/pending')

export const submitDecision = (incidentNumber, action, editedRca = '') =>
  api.post(`/decide/${incidentNumber}?action=${action}&edited_rca=${encodeURIComponent(editedRca)}`)

export const getNodeTrace = (incidentNumber) =>
  api.get(`/logs/${incidentNumber}`)