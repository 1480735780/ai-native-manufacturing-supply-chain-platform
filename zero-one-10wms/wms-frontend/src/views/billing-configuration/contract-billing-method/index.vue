<script lang="ts" setup>
definePage({
	meta: {
		menuType: "page",
		text: "合同计费方式",
		icon: "IconSetting",
	},
});
</script>

<template>
	<section class="plan-out">
		<el-alert type="warning" :closable="false" show-icon title="该页面在《版本计划》中为引用节点，归属待业务确认">
			<template #default>
				<p>
					「计费合同」在 emmx 中是<b>彩色引用节点</b>，按版本计划的计数规则<b>不计入 64 项</b>；其实际含义为「客户计费合同」：
					头表 <code>wm_cus_cost_h</code>（<code>cus_code</code>、<code>begin_date</code>、<code>end_date</code>、<code>cus_hetongid</code>、<code>fujian</code>），
					明细表 <code>wm_cus_cost_i</code>（<code>cost_code</code>、<code>cost_jg</code>、<code>cost_sl</code>、<code>cost_zk</code>、<code>cost_bhs</code>、<code>cost_hs</code>、<code>free_day</code>、<code>free_day2</code>）。
				</p>
				<p>
					当前 <code>wms-c4-billingconfig</code>、<code>wms-c4-billingtype</code>、<code>wms-c5-costconfig</code>、<code>wms-c5-costmanagement</code> 均<b>未提供</b>计费合同的任何接口，全库也<b>不存在合同主表</b>。
				</p>
				<p>
					处置建议：由业务确认归属（计费配置 或 计费管理），确认后按「合同头 + 计费明细」主子表立项，预估 2~3 人天。当前保留页面占位，避免菜单与路由缺失。
				</p>
			</template>
		</el-alert>
	</section>
</template>

<style lang="scss" scoped>
.plan-out {
	padding: 16px;

	p {
		margin: 6px 0;
		line-height: 1.7;
	}
}
</style>
