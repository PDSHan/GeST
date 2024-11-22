import matplotlib.pyplot as plt

# 数据
# x = [i for i in range(47)]
y = [float(i) for i in ['2.280816', '2.299658', '2.312967', '2.814005', '3.675169', '3.680811', '3.682449', '4.236943', '4.235546', '4.234033', '4.233040', '4.236646', '4.231874', '4.231387', '4.225495', '4.230626', '4.223010', '4.232836', '4.234814', '4.217006', '4.211804', '4.216351', '4.237341', '4.233307', '4.296225', '4.288964', '4.330096', '4.343961', '4.368278', '4.408180', '4.597053', '4.872761', '4.895185', '4.900502', '4.920979', '4.932812', '5.333434', '5.233612', '5.350221', '5.229246', '5.341495', '5.332619', '5.527337', '5.519946', '5.525895', '5.590710']]
x = [i for i in range(len(y))]
# 创建图形对象
plt.figure(figsize=(12, 6))

# 绘制散点图
plt.scatter(x, y, label='Optimal Fitness Value', color='blue', marker='o', s=10)

# 添加标题和标签
plt.title('Fig. Optimal Fitness Value over Generations while the size of population is 100.', fontsize=16)
plt.xlabel('Generations', fontsize=14)
plt.ylabel('Optimal Fitness Value', fontsize=14)

# 添加网格线
plt.grid(True)

# 显示图例
plt.legend()

# 显示图形
plt.show()

