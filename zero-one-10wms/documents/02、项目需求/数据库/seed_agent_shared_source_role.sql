-- 异常巡检 Agent 与页面共用数据源端点的资源/角色映射种子（ADR-021 收尾）
--   进货延时示警  GET /daycheck/delay/im-delay        （页面路由 /daily-check/shipment-delay-warn）
--   效期预警      GET /stock/expiry-warning/query-all  （页面路由 /customer-report/validity-warn）
--
-- 背景：oauth2 的 ResourcesServiceImpl.loadData() 从 t_s_function(functiontype=1, functionurl IS NOT NULL)
-- 加载资源，再经 TSRoleMapper.selectRoleByFunctionUrl 连接 t_s_role_function 得到 rolecode，
-- 写入 Redis 哈希 AUTH:RESOURCE_ROLES；网关 LoadResourcesDataImpl.loadRolesByUrlPath 按 URL 读取该映射。
-- 刷新：PUT oauth2:10400 /open/resources/cache/reload（经网关 10001 会 404，必须直连 oauth2）。
--
-- 为什么需要本种子：巡检 Agent 经网关调用 6 个数据源端点，其中 4 个此前已登记
-- （/daycheck/no-up/get-no-up-goods-page、/daycheck/yi-chang/get-yichang-down-page、
--   /daycheck/temperature/query、/dashboard/query-pend-snapshot），
-- 剩下本文件的 2 个端点未登记，当前只靠网关 deny-unregistered=false 放行并记 WARN。
-- 登记后 Agent 的全部调用路径都有明确的资源角色映射。
--
-- 【纯增量契约，与 seed_daycheck_f016_inspection_role.sql 一致】
-- 1) insp_read 角色 ID 按 rolecode 动态查询，必须恰好一行；为 0 或 >1 直接 SIGNAL 中止；
-- 2) 不使用任何 DELETE：既有角色/权限只增不减；
-- 3) ID 冲突（同一 function_id 指向别的 URL）或 URL 冲突（同一 URL 被别的 function_id 占用）→ SIGNAL 中止，
--    绝不覆盖既有映射；若 ID/URL 已存在但 functiontype<>1 也 SIGNAL 中止，避免 INSERT 被跳过后
--    OAuth 永远加载不到该资源的"假成功"；
-- 4) 不改写任何 MENU-* 菜单授权：共用端点只读取页面菜单的角色绑定，不写 MENU-* 行；
-- 5) 资源行与角色绑定均为纯增量 INSERT，已存在的绑定不重复写，可重复执行且幂等；
-- 6) 绑定 ID 冲突（同一 RF-* ID 已绑定到别的 function 或 functionid 为 NULL）→ SIGNAL 中止；
-- 7) 所有 INSERT 包在事务中，任一失败由 EXIT HANDLER ROLLBACK + RESIGNAL，杜绝部分写入。
-- 8) 两个端点都是「页面与巡检共用」，角色集合 = 页面菜单既有授权角色 ∪ insp_read。
--    共用端点若只绑 insp_read，页面现有用户会被网关判 403（网关自 2026-11-26 起真正按
--    AUTH:RESOURCE_ROLES 判 403）。页面菜单按 functionurl（前端路由）查找而不是写死菜单 ID，
--    因此同一页面挂在多个菜单下（如效期预警同时属于客户报表与预警管理）时角色取并集。
--    页面菜单授权以后有变更时，必须重跑本种子并刷新缓存，新增的页面角色才会同步到端点。
--
-- 执行方式：mysql CLI 可直接 source 本文件；程序化执行需按 DELIMITER 拆分。
--
-- 【手动激活步骤（本文件不自动执行，init.sh 也不执行种子或缓存刷新）】
-- (a) 在目标库执行种子：mysql -h <host> -u <user> -p <db> 后执行 source documents/02、项目需求/数据库/seed_agent_shared_source_role.sql；
-- (b) 种子写入 t_s_function/t_s_role_function 后，必须直连 oauth2 调用
--     PUT http://<oauth2 host>:10400/open/resources/cache/reload 刷新 AUTH:RESOURCE_ROLES 缓存；
--     经网关 :10001 转发该路径会返回 404，不可使用网关地址；
-- (c) init.sh 只做环境/基线/测试门禁，不会执行本种子，也不会触发缓存 reload，以上两步需人工完成。

USE `zo_wms`;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS `p_seed_agent_shared_source_role`;

DELIMITER //
CREATE PROCEDURE `p_seed_agent_shared_source_role`()
BEGIN
    DECLARE v_role_count INT DEFAULT 0;
    DECLARE v_probe VARCHAR(512);
    DECLARE v_probe_type TINYINT;
    DECLARE v_exists INT DEFAULT 0;

    -- 事务安全：任何预检/插入异常都回滚全部 INSERT，再原样抛出错误，避免部分写入。
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- (1) 按 rolecode 动态取唯一 insp_read 角色 ID；不创建角色、不硬编码 ID。
    SELECT COUNT(*) INTO v_role_count FROM `t_s_role` WHERE `rolecode` = 'insp_read';
    IF v_role_count <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: expected exactly one t_s_role row with rolecode=insp_read';
    END IF;
    SELECT `ID` INTO @insp_read_role_id FROM `t_s_role` WHERE `rolecode` = 'insp_read';

    -- (3) 逐端点预检：先判断行是否存在，再看内容。
    --     既有行若 functionurl / functiontype 为 NULL，不能用「IS NOT NULL」代替存在性判断，
    --     否则会跳过校验、INSERT ... WHERE NOT EXISTS 跳过插入、角色绑定照写并 COMMIT，
    --     结果是种子成功但 OAuth 加载不到该资源的假成功。

    -- 进货延时端点：ID 已存在时必须 URL 一致且可激活。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `ID` = 'FN-DAYCHECK-DELAY-IM-DELAY';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-DELAY-IM-DELAY appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SET v_probe_type = NULL;
        SELECT `functionurl`, `functiontype` INTO v_probe, v_probe_type
            FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-DELAY-IM-DELAY' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> '/daycheck/delay/im-delay' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-DELAY-IM-DELAY exists but functionurl is NULL or a different URL';
        END IF;
        IF v_probe_type IS NULL OR v_probe_type <> 1 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-DELAY-IM-DELAY exists but functiontype is NULL or <>1 (not activatable)';
        END IF;
    END IF;

    -- 进货延时端点：同一 URL 已绑定到别的 function id -> 中止，不覆盖。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/delay/im-delay' AND `ID` <> 'FN-DAYCHECK-DELAY-IM-DELAY';
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/delay/im-delay already mapped to a different function id';
    END IF;

    -- 进货延时端点：该 URL 下所有行的 functiontype 必须为 1，否则 OAuth 不会加载。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/delay/im-delay'
          AND (`functiontype` IS NULL OR `functiontype` <> 1);
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/delay/im-delay exists but functiontype is NULL or <>1 (not activatable)';
    END IF;

    -- 效期预警端点：ID 已存在时必须 URL 一致且可激活。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `ID` = 'FN-STOCK-EXPIRY-QUERY-ALL';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-STOCK-EXPIRY-QUERY-ALL appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SET v_probe_type = NULL;
        SELECT `functionurl`, `functiontype` INTO v_probe, v_probe_type
            FROM `t_s_function` WHERE `ID` = 'FN-STOCK-EXPIRY-QUERY-ALL' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> '/stock/expiry-warning/query-all' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-STOCK-EXPIRY-QUERY-ALL exists but functionurl is NULL or a different URL';
        END IF;
        IF v_probe_type IS NULL OR v_probe_type <> 1 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-STOCK-EXPIRY-QUERY-ALL exists but functiontype is NULL or <>1 (not activatable)';
        END IF;
    END IF;

    -- 效期预警端点：同一 URL 已绑定到别的 function id -> 中止，不覆盖。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/stock/expiry-warning/query-all' AND `ID` <> 'FN-STOCK-EXPIRY-QUERY-ALL';
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /stock/expiry-warning/query-all already mapped to a different function id';
    END IF;

    -- 效期预警端点：该 URL 下所有行的 functiontype 必须为 1，否则 OAuth 不会加载。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/stock/expiry-warning/query-all'
          AND (`functiontype` IS NULL OR `functiontype` <> 1);
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /stock/expiry-warning/query-all exists but functiontype is NULL or <>1 (not activatable)';
    END IF;

    -- (6) 预检：字面量绑定 ID 已存在时，必须指向本端点且绑定到 insp_read。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` = 'RF-DELAY-IM-INSPECT';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: RF-DELAY-IM-INSPECT appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SELECT `functionid` INTO v_probe FROM `t_s_role_function`
            WHERE `ID` = 'RF-DELAY-IM-INSPECT' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> 'FN-DAYCHECK-DELAY-IM-DELAY' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-DELAY-IM-INSPECT binding exists but functionid is NULL or a different function';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM `t_s_role_function`
                       WHERE `ID` = 'RF-DELAY-IM-INSPECT' AND `roleid` = @insp_read_role_id) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-DELAY-IM-INSPECT binding exists but is not bound to rolecode=insp_read';
        END IF;
    END IF;

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` = 'RF-EXP-QALL-INSPECT';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: RF-EXP-QALL-INSPECT appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SELECT `functionid` INTO v_probe FROM `t_s_role_function`
            WHERE `ID` = 'RF-EXP-QALL-INSPECT' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> 'FN-STOCK-EXPIRY-QUERY-ALL' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-EXP-QALL-INSPECT binding exists but functionid is NULL or a different function';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM `t_s_role_function`
                       WHERE `ID` = 'RF-EXP-QALL-INSPECT' AND `roleid` = @insp_read_role_id) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-EXP-QALL-INSPECT binding exists but is not bound to rolecode=insp_read';
        END IF;
    END IF;

    -- (8) 共用端点的角色集合 = 页面菜单既有授权角色 ∪ insp_read，所以页面菜单（按路由）必须存在。
    --      菜单缺失时无法推导页面角色；若退化为只绑 insp_read，网关会对页面现有用户返回 403，故中止。
    --      按路由查找而不是写死菜单 ID：同一页面可挂在多个菜单下，角色取并集。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daily-check/shipment-delay-warn';
    IF v_exists < 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: no page menu with functionurl=/daily-check/shipment-delay-warn, page roles of /daycheck/delay/im-delay must be re-derived';
    END IF;

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/customer-report/validity-warn';
    IF v_exists < 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: no page menu with functionurl=/customer-report/validity-warn, page roles of /stock/expiry-warning/query-all must be re-derived';
    END IF;

    -- 页面角色的绑定 ID 由 rolecode 拼出：RF-DELAY-IM-<ROLECODE> / RF-EXP-QALL-<ROLECODE>。
    -- rolecode 超过 16 个字符会超出 varchar(32)，中止而不是被截断成冲突 ID。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists
    FROM `t_s_role_function` mr
    JOIN `t_s_role` r ON r.`ID` = mr.`roleid`
    WHERE mr.`functionid` IN (
              SELECT `ID` FROM `t_s_function`
              WHERE `functionurl` IN ('/daily-check/shipment-delay-warn', '/customer-report/validity-warn'))
      AND CHAR_LENGTH(r.`rolecode`) > 16;
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: a page role rolecode is longer than 16 characters, derived binding id would exceed varchar(32)';
    END IF;

    -- 拼出的绑定 ID 若已被占用且指向别的函数（或 functionid 为 NULL）-> 中止，不覆盖。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` LIKE 'RF-DELAY-IM-%'
          AND (`functionid` IS NULL OR `functionid` <> 'FN-DAYCHECK-DELAY-IM-DELAY');
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: an RF-DELAY-IM-* binding exists but functionid is NULL or a different function';
    END IF;

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` LIKE 'RF-EXP-QALL-%'
          AND (`functionid` IS NULL OR `functionid` <> 'FN-STOCK-EXPIRY-QUERY-ALL');
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: an RF-EXP-QALL-* binding exists but functionid is NULL or a different function';
    END IF;

    -- (7) 资源行与绑定行的 INSERT 序列包在事务里，失败由 EXIT HANDLER 回滚。
    START TRANSACTION;

    -- (5) 纯增量插入资源行（存在即跳过，不覆盖既有字段）。
    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-DAYCHECK-DELAY-IM-DELAY', NULL, 2, '进货延时查询（巡检共用）', '99',
           '/daycheck/delay/im-delay', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-DELAY-IM-DELAY');

    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-STOCK-EXPIRY-QUERY-ALL', NULL, 2, '效期预警查询（巡检共用）', '100',
           '/stock/expiry-warning/query-all', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-STOCK-EXPIRY-QUERY-ALL');

    -- (5) 纯增量绑定：只新增缺失的绑定，保留既有其它角色不变。

    -- a) 进货延时端点（页面与巡检共用）：insp_read + 进货延时示警页面菜单的既有授权角色。
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-DELAY-IM-INSPECT', 'FN-DAYCHECK-DELAY-IM-DELAY', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-DAYCHECK-DELAY-IM-DELAY' AND `roleid` = @insp_read_role_id);

    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT DISTINCT CONCAT('RF-DELAY-IM-', UPPER(r.`rolecode`)), 'FN-DAYCHECK-DELAY-IM-DELAY', mr.`roleid`
    FROM `t_s_role_function` mr
    JOIN `t_s_role` r ON r.`ID` = mr.`roleid`
    WHERE mr.`functionid` IN (
              SELECT `ID` FROM `t_s_function`
              WHERE `functionurl` = '/daily-check/shipment-delay-warn')
      AND NOT EXISTS (
          SELECT 1 FROM `t_s_role_function` x
          WHERE x.`functionid` = 'FN-DAYCHECK-DELAY-IM-DELAY' AND x.`roleid` = mr.`roleid`);

    -- b) 效期预警端点（页面与巡检共用）：insp_read + 效期预警页面菜单的既有授权角色（多个菜单取并集）。
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-EXP-QALL-INSPECT', 'FN-STOCK-EXPIRY-QUERY-ALL', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-STOCK-EXPIRY-QUERY-ALL' AND `roleid` = @insp_read_role_id);

    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT DISTINCT CONCAT('RF-EXP-QALL-', UPPER(r.`rolecode`)), 'FN-STOCK-EXPIRY-QUERY-ALL', mr.`roleid`
    FROM `t_s_role_function` mr
    JOIN `t_s_role` r ON r.`ID` = mr.`roleid`
    WHERE mr.`functionid` IN (
              SELECT `ID` FROM `t_s_function`
              WHERE `functionurl` = '/customer-report/validity-warn')
      AND NOT EXISTS (
          SELECT 1 FROM `t_s_role_function` x
          WHERE x.`functionid` = 'FN-STOCK-EXPIRY-QUERY-ALL' AND x.`roleid` = mr.`roleid`);

    COMMIT;
END//
DELIMITER ;

CALL `p_seed_agent_shared_source_role`();
DROP PROCEDURE `p_seed_agent_shared_source_role`;
