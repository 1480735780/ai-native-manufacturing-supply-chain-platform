package com.zeroone.star.daycheck.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.YichangDown;
import com.zeroone.star.daycheck.mapper.YichangDownMapper;
import com.zeroone.star.daycheck.service.YichangDownService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.YichangDownDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * @author aaa
 * @version 1.0
 * @description TODO
 * @date 2025/2/24 09:14
 */
@Service
public class YichangDownServiceImpl implements YichangDownService {

    /**
     * 下载端点单页大小。整表分页拉取，不按"前 N 条"截断。
     */
    static final long DOWNLOAD_PAGE_SIZE = 1000L;

    /**
     * 单次导出的硬上限。超过即抛错而不是静默截断——导出文件看起来成功但缺数比失败更危险。
     * 上限同时约束内存：Service 累积 List、Controller 再累积完整 byte[]，必须有界。
     */
    static final int MAX_EXPORT_ROWS = 50000;

    @Resource
    YichangDownMapper yichangDownMapper;

    @Override
    public List<YichangDownDTO> getYichangDownPage(YichangDownQuery condition) {
        Page<YichangDown> page = new Page<>(condition.getPageIndex(), condition.getPageSize());
        // 调用分页查询方法
        Page<YichangDown> yichangDownPage = yichangDownMapper.getYichangDownPage(page, condition);
// 创建 DTO 列表
        ArrayList<YichangDownDTO> result = new ArrayList<>();

// 处理分页后的结果
        for (YichangDown yichangDown : yichangDownPage.getRecords()) {
            result.add(toDTO(yichangDown, false));
        }
        return result;
    }

    @Override
    public PageDTO<YichangDownDTO> getYichangDownPageDTO(YichangDownQuery condition) {
        Page<YichangDown> page = new Page<>(condition.getPageIndex(), condition.getPageSize());
        // 巡检专用语句：显式列 + 规则侧 Decimal 数量判定 + wtdg.id 稳定行键 + create_date/id 稳定排序
        Page<YichangDown> pages = yichangDownMapper.getYichangDownForInspection(page, condition);
        return PageDTO.create(pages, src -> toDTO(src, true));
    }

    /**
     * 实体 → DTO。BeanUtils 只按同名属性拷贝：实体 id 与 DTO rowId 名字不同，
     * 必须显式赋值，否则巡检侧拿到的 rowId 永远为 null。
     *
     * @param withIdentity 是否输出巡检行键（旧端点传 false，保持旧 JSON 不变）
     */
    static YichangDownDTO toDTO(YichangDown src, boolean withIdentity) {
        YichangDownDTO dto = new YichangDownDTO();
        BeanUtils.copyProperties(src, dto);
        dto.setBin_id(src.getBin_id_from());
        if (withIdentity) {
            dto.setRowId(src.getId());
        }
        return dto;
    }

    /**
     * 下载端点的数据源：每次调用都重新查询 mapper，绝不读取请求间共享的缓存字段。
     *
     * 原实现把最近一次分页结果存入单例服务的 Map 字段，请求 A 的列表会被请求 B 的
     * /download 导出，并发请求还会互相覆盖（跨请求状态泄漏）。download 端点
     * （GET /daycheck/yi-chang/download）没有携带上次查询的过滤参数，且引入请求作用域
     * 状态需要改接口签名和 Controller 契约，属于超出本修复范围的重构；因此这里采用
     * 确定性、无过滤的全新分页查询（按 create_date/id 稳定排序）。导出"当前条件下的数据"
     * 的精确过滤语义暂不可用，但这比跨请求泄漏安全：每个下载请求只拿到自己触发查询的数据。
     * 如果未来需要保留过滤条件，应通过请求作用域（如 DTO 参数）传递，而非单例字段。
     *
     * 分页语义：整表分页拉取直到取完，不再有"前 N 条后静默截断"的上限
     * （审计 m01655：超过上限即静默缺数，导出文件看起来成功但实际不全）。
     *
     * 一致性（审计 m01902）：OFFSET 分页在并发新增/删除时可能重复或漏行，因此这里
     * 1) 记录已见 wtdg.id，一旦跨页重复立即抛错——宁可让用户重试，也不导出可疑数据；
     * 2) 设置 MAX_EXPORT_ROWS 硬上限，超过即抛错。持续新增更晚记录不会让翻页无限进行，
     *    避免无限循环与 OOM。
     *
     * @throws IllegalStateException 导出结果超过上限，或翻页期间数据发生变更
     */
    @Override
    public List<YichangDown> getYichangDownDate() {
        List<YichangDown> all = new ArrayList<>();
        Set<String> seenIds = new HashSet<>();
        long pageIndex = 1L;
        while (true) {
            Page<YichangDown> page = new Page<>(pageIndex, DOWNLOAD_PAGE_SIZE);
            List<YichangDown> records =
                    yichangDownMapper.getYichangDownPage(page, new YichangDownQuery()).getRecords();
            if (records == null || records.isEmpty()) {
                break;
            }
            for (YichangDown record : records) {
                String id = record.getId();
                if (id != null && !seenIds.add(id)) {
                    throw new IllegalStateException(
                            "导出中止：翻页期间 wtdg.id=" + id + " 重复出现，数据在导出过程中发生变更，请重试");
                }
                all.add(record);
                if (all.size() > MAX_EXPORT_ROWS) {
                    throw new IllegalStateException(
                            "导出中止：命中的行数超过单次导出上限 " + MAX_EXPORT_ROWS
                                    + " 条，请缩小范围或分批导出（不会静默截断）");
                }
            }
            // 不足一页说明已经取完；直接用返回条数判断，避免依赖 total 的一致性。
            if (records.size() < DOWNLOAD_PAGE_SIZE) {
                break;
            }
            pageIndex++;
        }
        return all;
    }
}
