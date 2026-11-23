package com.zeroone.star.stockln.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.zeroone.star.project.dto.j6.stockln.ToAcceptDTO;
import com.zeroone.star.project.query.j6.stockln.InNoticeQuery;
import com.zeroone.star.project.vo.j6.stockln.InNoticePageVO;

/**
 * 入库通知明细服务
 */
public interface InNoticeService extends IService<ToAcceptDTO> {

    InNoticePageVO getInNoticeItems(InNoticeQuery query, int page, int size);

    /**
     * 按查询条件导出数据
     *
     * @param query 查询条件
     * @return Excel 字节数组
     */
    byte[] exportInNotice(InNoticeQuery query);
}
