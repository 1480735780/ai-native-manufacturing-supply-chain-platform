package com.zeroone.star.project.dto.j5.basezl.rfid;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Getter;
import lombok.Setter;
import lombok.ToString;

/**
 * 功能：
 * 作者：蕉太狼殿下
 * 日期：2025/2/22 16:30
 */
@ToString
@Getter
@Setter
@ApiModel("RFID下拉列表模型")
public class RFIDListDTO extends RFIDBaseDTO{

    /**
     * 主键。列表行必须带主键，前端才能做单条删除、批量删除和“勾选优先”导出。
     */
    @ApiModelProperty(value = "主键", example = "1")
    private Long id;
}
