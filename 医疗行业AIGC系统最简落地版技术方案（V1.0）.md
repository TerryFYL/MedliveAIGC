---
title: 医疗行业AIGC系统最简落地版技术方案（V1.0）
authors: 架构组
status: Draft
last_updated: 2025-10-20
---

# 医疗行业AIGC系统最简落地版技术方案（V1.0）

> 由“最终报告”与“合并稿”比对融合而成：保留已达成共识与可直接落地的做法，存异项以“触发条件”形式保留可切换路线。

## 0. 执行摘要（定案与开关）
- 架构：K8s + Istio 微服务与事件驱动；API 网关统一鉴权与租户校验；全链路可观测（日志/指标/追踪）。
- 多租户：默认 Schema-per-tenant；高保租户 DB-per-tenant + BYOK；核心数据域不使用 RLS。
- 工作流：Temporal 主编排（含 User Task/HITL）；Airflow 处理批/离线；流程版本化与轻量可视化（React Flow/JSON-DSL）。
- 意图与路由：两阶段理解（高置信 NLU→直达；低置信→LLM 澄清/判别）；不确定性触发 HITL。
- LLM：混合部署（PHI/高风险本地，非PHI/低风险云API）；统一 LLM Proxy 做路由/降级/缓存；RAG 强制引注，高风险多代理复核；质量与成本双KPI。
- 知识：向量库 + 医疗知识图谱融合；FHIR 治理元数据沉淀模型版本、证据、置信度与签批链。
- HITL：Tiptap + Yjs 协同编辑；电子签名与版本比对；抽检 ≥ 5%。
- 监控：Prometheus/Grafana、ELK、OpenTelemetry/Jaeger；AI 质量看板 + 成本看板。
- 选项开关（触发后启用）：当“业务侧自助改流程月均>10 或 非技术编辑者>5”→ 引入 Camunda/Conductor 可视化；当监管或主权更强 → 提升本地模型优先级；云API扩大需满足去标识/不落盘/成本延迟阈。

## 1. 目标与边界
- 能力范围：通用意图理解、多步工具链编排、可追溯生成、严格合规、HITL 校验闭环、SLA/成本/质量监控。
- 非目标：不提供自动诊断决策；不替代临床最终裁量；无 EHR 写回不下达治疗方案。
- MVP 指标：医生文书人工修改率 ≤ 35%；首响应 ≤ 2.5s；端到端 ≤ 60s；事实错误率 ≤ 5%，幻觉率 ≤ 3%；审计覆盖 100%，PHI 外发 0；千请求成本较基线下降 ≥ 20%。

## 2. 架构与多租户
- 分层：接入（OAuth2/OIDC、WAF、租户校验、配额/风控）｜编排（Temporal/Kafka）｜智能（LLM Proxy/RAG/判别器）｜工具（检索/提取/药典/渲染/签名）｜数据（OLTP/对象存储/向量库/知识图谱/FHIR治理元数据）｜可观测与合规（Prometheus/ELK/OTel/KMS/HSM）｜前台（工作台/HITL 审核台）。
- 多租户：默认 Schema-per-tenant；高保租户 DB-per-tenant + BYOK；应用层强租户上下文校验；禁跨租户查询。
- 高可用：无状态服务 HPA；长耗时异步与队列削峰；熔断/退避重试；存储冷热分层与多副本；同城双活 + 异地冷备（RPO/RTO 入 SLA）。

## 3. 意图理解与路由
- 混合 NLU：规则/小模型承担实体抽取与标准化；LLM 处理低置信与复杂语义，两阶段判别。
- 多轮管理：结构化流程用状态机/规则；开放问答用 Memory 摘要 + 工具调用；话题漂移检测与上下文重置。
- 模糊与红旗：置信度 < 阈值 → 澄清/HITL；红旗词（处方调整/急危重症）→ 直达 HITL；无法分类 → 扩充意图库与训练集。

## 4. 工作流编排
- 引擎：Temporal 负责实时交互/长流程/补偿/信号/超时/HITL；Airflow 负责批/ETL/索引构建。
- 版本与灰度：工作流定义版本化；新实例走新版本，旧实例原路结束；轻量可视化（React Flow/GoJS + JSON-DSL）。
- 存异位：高频自助改流程/强运营视图 → 引入 Camunda 8（Zeebe）或 Conductor。

## 5. LLM 集成与质量控制
- 路由：数据分级 × 任务难度 × 成本阈值；PHI/高风险优先本地 7B–13B；非PHI/低风险用签 BAA 的云API。
- Proxy：统一路由矩阵、熔断降级、AB 复试、语义缓存、成本打点。
- Prompt/RAG/Judge：系统角色 + 模板 + few-shot；RAG 强制引注（药典/指南/文献）；判别器做事实一致性/禁词/PII 检测；高风险多代理复核（LLM-as-a-judge/规则）。
- KPI/降级：幻觉率、事实错、HITL 率、拒绝率、延迟、P99、成本；超阈自动降级或强制 HITL。

## 6. 医疗知识与标准
- 向量库：Qdrant/Weaviate/Milvus（多租户命名空间）。
- 权威源：药品（国家药典/DrugBank）、疾病（ICD/SNOMED）、指南（学会/权威期刊）、不良反应/相互作用。
- 知识图谱：药物-疾病-症状-禁忌关系；术语标准化（ICD-10/11、SNOMED CT、LOINC、RxNorm）。
- FHIR 治理：按 FHIR AI Transparency 捕获模型名/版本、提示摘要、证据ID、置信度、审签链、输出哈希。

## 7. 人机协同（HITL）
- 触发：不确定性高、红旗意图、法规要求、抽检 ≥ 5%。
- 编辑器：Tiptap + Yjs（或等价 CRDT），多人协同、变更高亮、术语侧栏、模板片段。
- 签名与版本：电子签名、全版本比对；不可篡改审计（WORM/时间戳）。
- 回流：AI 初稿 vs 最终稿差异入训练库；错误类型与评分用于提示与微调。

## 8. 监控与运维
- 指标：系统（QPS/延迟/错误）、AI（准确/幻觉/HITL）、成本（Token/GPU/调用）、合规（PHI 访问、审计覆盖）。
- 平台：Prometheus/Grafana、ELK、OTel/Jaeger、成本看板；GPU/模型漂移/数据漂移监测。
- 告警与自愈：SLO 违约、幻觉/成本超阈、外部 API 异常；健康检查、HPA、熔断/退避重试、备份模型降级、队列背压；Chaos/故障注入与 Runbook。

## 9. 安全与合规
- 最小必要与知情同意；传输/存储加密（TLS/KMS/HSM）。
- RBAC/ABAC 与细粒度审计；密钥轮换；跨境合规（PIPL/GDPR/HIPAA/BAA）。
- 第三方模型：不落盘、数据不用于训练、专线/私有连接；日志与审计保留期、WORM/存证（可选区块链哈希）。

## 10. 实施路线（PoC → MVP → Prod）
- T0（0–8 周，PoC）：端到端链路（Temporal + RAG + HITL + 合规日志）；LLM Proxy；三看板雏形；目标：修改率 ≤ 50%，事实错 ≤ 10%，P95 ≤ 5s。
- T1（9–20 周，MVP）：扩两类意图（文书/用药解读）；上线本地 7B–13B；多租户 Schema；审计全覆盖；目标：修改率 ≤ 35%，事实错 ≤ 5%，幻觉 ≤ 3%，成本 ↓ 20%。
- T2（21–32 周，Prod）：高保租户 DB-per-tenant + BYOK；若触发条件达标引入可视化编排；目标：SLA 99.9%，端到端 ≤ 45s，合规 0 事故。

## 11. 最低落地包（两周内交付）
- 端到端样例链路：Temporal（含 User Task）、RAG 引注、HITL 编辑器、合规日志。
- LLM Proxy & 路由矩阵：按“数据分级 × 任务难度 × 成本阈值”。
- 三看板：系统性能、AI 质量（幻觉/审阅率/事实错）、成本（Token/GPU）。
- 多租户骨架：Schema-per-tenant + 高保客户 DB-per-tenant 样例 + BYOK 流程。
- 合规清单与审计 Schema（FHIR 元数据）。

## 12. 选项开关（评审时决策）
- BPMN/Conductor：当“月 > 10 次业务侧自助改流程”或“> 5 位非技术编辑者”或“需要强运营视图”。
- 云 API 扩大：质量显著提升且去标识/不落盘达标，成本/延迟在阈内。
- 自研/微调升级：当“HITL 修改率在 2 个迭代难以下降”或“子域问答准确卡在阈值”。

## 13. 规则片段（可直接落库/DSL）
```pseudo
# HITL 触发
if intent in ['诊断建议','处方调整'] 
   or uncertainty > 0.4 
   or missing_citations 
   or red_flags:
    USER_TASK('临床复核', sla='24h', escalate='科主任')

# 模型降级/切换
if latency_p95 > 5s or cost_per_1k > THRESH or hallucination_rate > THRESH:
    route.switch(model_tier - 1)

# 审计元数据（入 FHIR 扩展/治理仓）
audit = {
  request_id, tenant_id, model_name, model_version,
  prompt_hash, citations[], confidence, reviewer_id,
  sign_hash, output_hash, timestamp
}
```

## 14. 融合说明（简要）
- “最终报告”中的 FHIR 治理、WORM 不可篡改与韧性感知 MLOps 要点已纳入。
- “合并稿”的两阶段路由、Temporal 主编排、选项开关与指标体系予以保留。
- 删除冗长评估表与重复论证，统一术语与触发条件表达。
- 以“最低落地包 + 路线图 + 规则片段”作为最直接的落地交付骨架。