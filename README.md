1:这是一个大二实训的人事管理系统,包含基本的登录,注册功能,以及普通用户登录后的用户界面,以及管理员登录后的管理界面
需要采用的有  mysql8.0,py3,8-3,10,socket,  hmac,hashlib里面的MD5(不安全,可以人为更换成哈希)
2:大致轮廓如下:
![image](https://github.com/user-attachments/assets/d3ae2d85-313a-4a85-8b4e-dcecb4dbfdf5)
![image](https://github.com/user-attachments/assets/9a4f71ac-e831-4393-931a-6fdbee518c72)
![image](https://github.com/user-attachments/assets/18daa66d-7c4d-4fd3-8e23-2bebd3039182)

3:(1).项目运行的前提是 先数据库初始化: 会默认创建works 数据库,里面的表如 sql文件展示 可以通过数据库脚本进行一键创造.再插入数据时,请关注这个外键的影响,注意插入顺序
以及这个db_connnect 这个的关键参数修改
(2).管理员通信的模块默认时本地回环地址127.0.0.1,如果想真正修改成服务器,请记得修改  补充的有:如果是阿里的云服务器,因为他这安全过滤规则,不可以通过这个服务器通信模块进行远程命令执行
如果是本地的,不可以获取自己外界出口公网ip(这个首先的先进行网络通信)

最后:因为是完成作业,所有功能不完善或者具有bug,望海涵!



