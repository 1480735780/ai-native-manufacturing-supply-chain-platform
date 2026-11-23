package com.zeroone.star.stockln.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.dto.j6.stockln.InNoticeVO;
import com.zeroone.star.project.dto.j6.stockln.ToAcceptDTO;
import com.zeroone.star.project.query.j6.stockln.InNoticeQuery;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * <p>
 * 描述：入库通知明细数据访问层
 * </p>
 *
 * @author [Susu]
 * @version 1.0.0
 */
@Repository
@Mapper
public interface InNoticeMapper extends BaseMapper<ToAcceptDTO> {

    Page<InNoticeVO> selectInNoticePage(Page<InNoticeVO> page, @Param("query") InNoticeQuery query);

    List<InNoticeVO> selectInNoticeList(@Param("query") InNoticeQuery query);
}

