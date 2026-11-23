-- ============================================================================
-- 菜单收口：移除已合并的「商品明细」独立页
--
-- 背景：按产品决策「商品详情合并为商品页的详情抽屉」，前端页面
--       wms-frontend/src/views/base-data/Commodity-detail/index.vue 已删除。
--       前端路由由文件自动生成，页面删掉路由即消失；
--       但若某个环境的 t_s_function 里手工注册过「商品明细」菜单，
--       该菜单仍会显示并指向一个已不存在的路由（点击白屏）。
--       本脚本负责清掉这类残留菜单及其角色绑定。
--
-- 特性：幂等。没有残留数据时执行不报错、不删除任何有效数据。
-- 执行顺序：① 先查 → ② 备份 → ③ 删角色绑定 → ④ 删菜单 → ⑤ 复查
-- ============================================================================

-- ① 先查：确认到底有没有残留（重点看 functionurl 是否指向已删除的页面）
SELECT id, functionname, functionurl, parentfunctionid, functiontype
FROM t_s_function
WHERE functionname LIKE '%商品明细%'
   OR functionurl LIKE '%Commodity-detail%';

-- ② 备份：把要删的记录留档（备份表不存在时才建，避免覆盖上一次备份）
CREATE TABLE IF NOT EXISTS t_s_function_bak_20261122 LIKE t_s_function;

INSERT INTO t_s_function_bak_20261122
SELECT *
FROM t_s_function
WHERE functionname LIKE '%商品明细%'
   OR functionurl LIKE '%Commodity-detail%';

-- ③ 删角色-菜单绑定（必须先删，否则留下孤儿绑定，角色授权页会报错）
DELETE rf
FROM t_s_role_function rf
INNER JOIN t_s_function f ON f.id = rf.functionid
WHERE f.functionname LIKE '%商品明细%'
   OR f.functionurl LIKE '%Commodity-detail%';

-- ④ 删菜单本身
DELETE f
FROM t_s_function f
WHERE f.functionname LIKE '%商品明细%'
   OR f.functionurl LIKE '%Commodity-detail%';

-- ⑤ 复查：两条语句都应返回 0 行
SELECT COUNT(*) AS remain_menu
FROM t_s_function
WHERE functionname LIKE '%商品明细%' OR functionurl LIKE '%Commodity-detail%';

SELECT COUNT(*) AS remain_role_binding
FROM t_s_role_function rf
LEFT JOIN t_s_function f ON f.id = rf.functionid
WHERE f.id IS NULL;

-- ============================================================================
-- 回滚（如需恢复）：从备份表还原菜单，再按需重新给角色授权
-- ----------------------------------------------------------------------------
-- INSERT INTO t_s_function SELECT * FROM t_s_function_bak_20261122;
-- 前端页面恢复：git checkout HEAD -- wms-frontend/src/views/base-data/Commodity-detail
-- ============================================================================
