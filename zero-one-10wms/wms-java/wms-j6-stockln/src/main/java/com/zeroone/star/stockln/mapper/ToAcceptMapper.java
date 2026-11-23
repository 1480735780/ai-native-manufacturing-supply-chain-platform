package com.zeroone.star.stockln.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zeroone.star.project.dto.j6.stockln.ToAcceptDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.springframework.stereotype.Repository;

@Repository
@Mapper
public interface ToAcceptMapper extends BaseMapper<ToAcceptDTO> {

    @Select("select cus_code from wm_im_notice_h where notice_id = #{imNoticeId} limit 1")
    String selectCusCodeByNoticeId(String imNoticeId);
}
