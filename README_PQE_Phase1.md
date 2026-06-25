# PQE Phase 1 MVP 使用说明

## 功能

`pqe_phase1_mvp.py` 实现第一阶段可用版本：

- 自动读取当前目录中的 CPK 报告和 FAI 报告
- 解析 CPK/FAI 模板中的 Part 信息、穴位、SPC、FAI、规格、公差、测量样本
- 重新计算 `Max`、`Min`、`Mean`、`Median`、`Std Dev`、`Cp`、`Cpk`、`Yield`
- 统计 FAI OK/NG、SPC OK/NG
- 筛选 `Cpk < 1.33` 的尺寸
- 基于现有样本计算满足目标 CPK 的建议公差
- 输出汇总 Excel 文件

## 运行环境

按现有项目要求，使用 `conda yolov5` 环境执行。

## 快速运行

在本目录执行：

```bash
conda run -n yolov5 python pqe_phase1_mvp.py --output PQE_Phase1_Summary.xlsx
```

脚本会自动识别文件名中包含 `CPK` 和 `FAI` 的 Excel 文件。

## 指定文件运行

```bash
conda run -n yolov5 python pqe_phase1_mvp.py \
  --cpk-file "APHZ_M2177 MP2_T1_806-63370_05_C2177P606_ARM BASE(Re-striking)_CPK_Report_20260525.xlsx" \
  --fai-file "APHZ_M2177 MP2_T1_806-63370_05_C2177P606_ARM BASE(Re-striking)_FAI_Report_20260523.xlsm" \
  --target-cpk 1.33 \
  --output PQE_Phase1_Summary.xlsx
```

## 输出工作表

| Sheet | 内容 |
|---|---|
| `Summary` | 总体统计，包括 CPK/FAI 文件、目标 CPK、低 CPK 数、FAI OK/NG、SPC OK/NG |
| `CPK_Summary` | CPK 与 Raw data 的逐尺寸统计结果 |
| `CPK_LowRisk` | `Cpk < target` 的尺寸清单 |
| `Tolerance_Proposal` | 低 CPK 尺寸的建议公差 |
| `FAI_OK_NG` | FAI 逐尺寸 OK/NG 统计 |
| `SPC_OK_NG` | 按穴位和 SPC 分组的 OK/NG 统计 |
| `Worst_Cavity` | 同一 SPC/FAI 在多穴中的最差穴位 |
| `Raw_Normalized_CPK` | 标准化后的 CPK 数据，含样本值 JSON |

## 当前样例输出结果

当前目录样例文件生成的 `PQE_Phase1_Summary.xlsx` 验证结果：

- CPK 记录：4392 行
- FAI 记录：712 行
- `Cpk < 1.33`：426 行
- FAI 样本：当前样例全部 OK

## 说明

- 脚本直接解析 Excel OOXML，不依赖 Excel 公式缓存。
- 统计结果基于原始样本重新计算。
- GD&T 按非负偏差处理，默认规格为 `[0, +Tol]`。
- Tolerance 按 `Nominal + Tol-` 到 `Nominal + Tol+` 判断。
- SPC 分组逻辑：同一穴位 + SPC 下任意 FAI NG，则 SPC NG。
