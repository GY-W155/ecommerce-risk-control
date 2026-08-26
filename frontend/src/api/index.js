import request from '../utils/request'

// ---------- 风险检查 ----------
export const riskCheck = (data) => request.post('/risk/check', data)
export const getAssessment = (id) => request.get(`/risk/assessments/${id}`)

// ---------- 规则管理 ----------
export const listRules = () => request.get('/risk/rules')
export const createRule = (data) => request.post('/risk/rules', data)
export const updateRule = (data) => request.post('/risk/rules/update', data)
export const changeRuleStatus = (data) => request.post('/risk/rules/status', data)
export const deleteRule = (id) => request.post('/risk/rules/delete', { id })

// ---------- 案件审核 ----------
export const listCases = (params) => request.get('/risk/cases', { params })
export const getCaseDetail = (id) => request.get(`/risk/cases/${id}`)
export const reviewCase = (data) => request.post('/risk/cases/review', data)

// ---------- 黑名单 ----------
export const listBlacklists = (params) => request.get('/risk/blacklists', { params })
export const createBlacklist = (data) => request.post('/risk/blacklists', data)
export const deleteBlacklists = (ids) => request.post('/risk/blacklists/delete', { ids })
export const importBlacklists = (data) => request.post('/risk/blacklists/import', data)

// ---------- 画像 / 看板 ----------
export const getUserProfile = (userId) => request.get(`/risk/users/${userId}/profile`)
export const getDashboard = () => request.get('/risk/dashboard')
