<script lang="ts" setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { queryCangweiMap } from "@/apis/chuweiguanli";

definePage({
	meta: {
		menuType: "page",
		text: "仓位图",
		icon: "IconSetting",
	},
});

interface BinCell {
	bin_store: string;
	ku_wei_bian_ma: string;
	xnode: string;
	ynode: string;
	znode: string;
	colour: string;
	tincount: string;
}

const loading = ref(false);
const allBins = ref<BinCell[]>([]);
const storeFilter = ref("");
const znodeFilter = ref("");

/** 仓库选项（从数据中提取） */
const storeOptions = computed(() =>
	Array.from(new Set(allBins.value.map(item => item.bin_store).filter(Boolean))),
);

/** 楼层选项（当前仓库下的 znode） */
const znodeOptions = computed(() => {
	const list = allBins.value
		.filter(item => !storeFilter.value || item.bin_store === storeFilter.value)
		.map(item => item.znode)
		.filter(Boolean);
	return Array.from(new Set(list)).sort();
});

/** 过滤后的储位 */
const filteredBins = computed(() =>
	allBins.value.filter(
		item =>
			(!storeFilter.value || item.bin_store === storeFilter.value) &&
			(!znodeFilter.value || item.znode === znodeFilter.value),
	),
);

/** 是否有真实坐标数据（数据库未配置 x/y 时自动按顺序生成网格） */
const hasCoord = computed(() =>
	filteredBins.value.some(item => String(item.xnode || "") !== "" && String(item.ynode || "") !== ""),
);

/** 网格行（X 坐标）；无坐标时按每行 8 个生成虚拟行号 */
const xNodes = computed(() => {
	if (!hasCoord.value) {
		const rows = Math.ceil(Math.max(filteredBins.value.length, 1) / 8);
		return Array.from({ length: rows }, (_, i) => String(i + 1));
	}
	return Array.from(new Set(filteredBins.value.map(item => item.xnode))).sort(
		(a, b) => Number(a) - Number(b),
	);
});

/** 网格列（Y 坐标）；无坐标时虚拟为 8 列 */
const yNodes = computed(() => {
	if (!hasCoord.value) return Array.from({ length: 8 }, (_, i) => String(i + 1));
	return Array.from(new Set(filteredBins.value.map(item => item.ynode))).sort(
		(a, b) => Number(a) - Number(b),
	);
});

/** 储位格子颜色 */
const commonColors: Record<string, string> = {
	red: "#f56c6c", 红: "#f56c6c",
	blue: "#409eff", 蓝: "#409eff",
	green: "#67c23a", 绿: "#67c23a",
	yellow: "#e6a23c", 黄: "#e6a23c",
	orange: "#f0883a", 橙: "#f0883a",
	gray: "#909399", 灰: "#909399", 灰色: "#909399",
	white: "#ffffff", 白: "#ffffff",
	purple: "#9254de", 紫: "#9254de",
	pink: "#f472b6", 粉: "#f472b6",
};
const cellColor = (cell: BinCell) => {
	const raw = String(cell.colour || "").trim();
	if (/^#[0-9a-f]{3,8}$/i.test(raw) || /^rgb/i.test(raw)) return raw;
	const lower = raw.toLowerCase();
	if (commonColors[lower]) return commonColors[lower];
	if (commonColors[raw]) return commonColors[raw];
	// 无有效颜色时按托盘数着色
	const tin = Number(cell.tincount);
	if (Number.isFinite(tin) && tin > 0) return "#67c23a";
	return "#dcdfe6";
};

/** 网格中某行某列的储位 */
const cellAt = (x: string, y: string) => {
	if (!hasCoord.value) {
		const cols = 8;
		const index = (Number(x) - 1) * cols + (Number(y) - 1);
		return filteredBins.value[index];
	}
	return filteredBins.value.find(item => item.xnode === x && item.ynode === y);
};

const cellText = (value: any) =>
	value === null || value === undefined || value === "" ? "-" : value;

const loadData = () => {
	loading.value = true;
	queryCangweiMap(
		{},
		data => {
			const rows: BinCell[] = Array.isArray(data) ? data : data?.rows || [];
			allBins.value = rows;
			loading.value = false;
			if (!rows.length) {
				ElMessage.info("暂无储位数据");
			}
		},
		() => {
			loading.value = false;
			ElMessage.error("仓位数据加载失败");
		},
	);
};

const handleStoreChange = () => {
	znodeFilter.value = "";
};

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="cangwei-map">
		<h2>仓位图</h2>
		<div class="toolbar">
			<el-select v-model="storeFilter" placeholder="选择仓库" clearable style="width: 180px" @change="handleStoreChange">
				<el-option v-for="item in storeOptions" :key="item" :label="item" :value="item" />
			</el-select>
			<el-select v-model="znodeFilter" placeholder="选择楼层(Z)" clearable style="width: 160px">
				<el-option v-for="item in znodeOptions" :key="item" :label="'第 ' + item + ' 层'" :value="item" />
			</el-select>
			<el-button :loading="loading" @click="loadData">刷新</el-button>
			<span class="legend">
				<span class="legend-item"><i class="dot" style="background:#67c23a"></i>有托盘/占用</span>
				<span class="legend-item"><i class="dot" style="background:#dcdfe6"></i>空闲/无颜色</span>
			</span>
		</div>

		<div v-loading="loading" class="map-wrap">
			<div v-if="xNodes.length === 0" class="empty">暂无数据</div>
			<div v-else class="grid" :style="{ gridTemplateColumns: `60px repeat(${yNodes.length}, 46px)` }">
				<!-- 表头行 -->
				<div class="corner"></div>
				<div v-for="y in yNodes" :key="'h' + y" class="axis-cell">{{ y }}</div>
				<!-- 每行 -->
				<template v-for="x in xNodes" :key="'r' + x">
					<div class="axis-cell">{{ x }}</div>
					<el-tooltip
						v-for="y in yNodes"
						:key="'c' + x + '-' + y"
						:content="cellAt(x, y) ? `${cellAt(x, y)!.bin_id || cellAt(x, y)!.ku_wei_bian_ma}  ${cellText(cellAt(x, y)!.bin_store)}  托盘:${cellText(cellAt(x, y)!.tincount)}  颜色:${cellText(cellAt(x, y)!.colour)}` : '无储位'"
						placement="top"
					>
						<div
							class="cell"
							:class="{ occupied: cellAt(x, y) }"
							:style="cellAt(x, y) ? { background: cellColor(cellAt(x, y)!) } : {}"
						>
							<span v-if="cellAt(x, y)">{{ cellAt(x, y)!.bin_id || cellAt(x, y)!.ku_wei_bian_ma }}</span>
						</div>
					</el-tooltip>
				</template>
			</div>
		</div>
	</section>
</template>

<style lang="scss" scoped>
.cangwei-map {
	width: 100%;
	.toolbar {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 10px;
		margin: 12px 0;
		.legend {
			display: flex;
			gap: 14px;
			margin-left: 16px;
			color: #606266;
			font-size: 12px;
			.legend-item {
				display: flex;
				align-items: center;
				gap: 5px;
				.dot {
					display: inline-block;
					width: 12px;
					height: 12px;
					border-radius: 2px;
					border: 1px solid #c0c4cc;
				}
			}
		}
	}
	.map-wrap {
		overflow: auto;
		border: 1px solid #e4e7ed;
		border-radius: 4px;
		padding: 12px;
		min-height: 300px;
		.empty {
			text-align: center;
			color: #909399;
			padding: 60px 0;
		}
		.grid {
			display: grid;
			gap: 4px;
			width: max-content;
			.axis-cell {
				display: flex;
				align-items: center;
				justify-content: center;
				font-size: 12px;
				color: #909399;
				height: 38px;
			}
			.corner {
				height: 38px;
			}
			.cell {
				width: 46px;
				height: 38px;
				display: flex;
				align-items: center;
				justify-content: center;
				font-size: 10px;
				border: 1px solid #e4e7ed;
				border-radius: 3px;
				background: #f5f7fa;
				color: #303133;
				cursor: pointer;
				overflow: hidden;
				white-space: nowrap;
				text-overflow: ellipsis;
				&.occupied:hover {
					outline: 2px solid #409eff;
				}
			}
		}
	}
}
</style>
