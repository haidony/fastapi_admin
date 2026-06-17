<template>
  <div class="fa-card p-5 pb-3 h-53 max-sm:h-53 flex flex-col">
    <div class="fa-card-header">
      <div class="title">
        <h4>
          快速链接
          <ElTooltip content="在顶部标签栏左侧星标上点击，可加入或取消收藏" placement="top">
            <ElIcon :size="14"><QuestionFilled /></ElIcon>
          </ElTooltip>
        </h4>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto -mr-1 pr-1">
      <div v-if="quickLinks.length > 0" class="grid grid-cols-4 gap-2">
        <div
          v-for="item in linksWithColor"
          :key="item.id || item.href"
          class="quick-link-item relative flex flex-col items-center gap-1 py-2 px-1 rounded-lg cursor-pointer hover:bg-(--el-fill-color-lighter) transition-colors"
          @click="handleClick(item)"
        >
          <span
            class="flex items-center justify-center w-9 h-9 rounded text-white"
            :style="{ backgroundColor: item._color }"
          >
            <FaMenuRouteIcon :icon="item.icon || 'menu'" :size="18" />
          </span>
          <span class="text-xs text-center leading-tight line-clamp-2 text-g-700">{{
            item.title
          }}</span>
          <span class="quick-link-close" @click.stop="handleRemove(item)">
            <ElIcon :size="10"><Close /></ElIcon>
          </span>
        </div>
      </div>
      <ElEmpty v-else description="暂无链接" :image-size="50" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { Close, QuestionFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { quickStartManager, type QuickLink } from "@utils";

const router = useRouter();

const quickLinks = ref<QuickLink[]>(quickStartManager.getQuickLinks());

const QUICK_LINK_PALETTE = ["#4080ff", "#23c343", "#ff9a2e", "#f76560", "#a9aeb8", "#00b42a"];
const linksWithColor = computed(() =>
  quickLinks.value.map((item, i) => ({
    ...item,
    _color: QUICK_LINK_PALETTE[i % QUICK_LINK_PALETTE.length],
  }))
);

const handleClick = (item: QuickLink) => {
  if (item.href) {
    router.push(item.href).catch(() => {
      ElMessage.warning(`路由 ${item.href} 不存在，请检查配置`);
    });
  } else {
    ElMessage.info(`${item.title} 功能待开发`);
  }
};

const handleRemove = (item: QuickLink) => {
  if (item.id) {
    quickStartManager.removeQuickLink(item.id);
  } else if (item.href) {
    quickStartManager.removeQuickLinkByHref(item.href);
  }
};

const updateQuickLinks = (links: QuickLink[]) => {
  quickLinks.value = links;
};

onMounted(() => {
  quickStartManager.addListener(updateQuickLinks);
});
onUnmounted(() => {
  quickStartManager.removeListener(updateQuickLinks);
});
</script>

<style scoped>
.quick-link-close {
  position: absolute;
  top: -4px;
  right: -4px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  background: var(--el-bg-color);
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.2s;
}

.quick-link-item:hover .quick-link-close {
  opacity: 1;
}

.quick-link-close:hover {
  color: var(--el-color-danger);
  background-color: var(--el-color-danger-light-9);
}
</style>
