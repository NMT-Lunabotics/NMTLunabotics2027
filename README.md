# NMTLunabotics2027
Welcome to the 2027 New Mexico Tech Lunabotics Capstone Design Team repository. This is where software and supporting resources are stored during the development of our competition robot.

## Setup github on linux

1. Install github on linux
```
sudo apt update
sudo apt install git
```

2. Configure global github infomation
```
git config --global user.name "username"
git config --global user.email "email@student.nmt.edu"
```

3. Clone github repository 
```
git clone https://github.com/NMT-Lunabotics/NMTLunabotics2027
cd NMTLunabotics2027/
git remote set-url origin git@github.com:NMT-Lunabotics/NMTLunabotics2027.git
```

4. Create public ssh key
```
ssh-keygen -t ed25519 -C "email@student.nmt.edu"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

5. Copy ssh key excluding email, the key should look like: (`ssh-ed25519 AFADC3NzaC1lLDI1NTE5ABCAIA2YBiHF60J3OgnU1R8LbIU6zKm3KGPFzzGmVpQxi9cH`)
```
cat ~/.ssh/id_ed25519.pub
```

6. Vist [Github ssh key](https://github.com/settings/ssh/new), And create new ssh key using the previous copyied key. 

7. After github registers your key, check to ensure you are authenticated, it will return `successfully authenticated`
```
ssh -T git@github.com
```

***

- To pull recent changes
```
git pull
```

- To commit and push your recent changes
```
git add .
git commit -m "test file"
git push
```

***

- If you use visual stuido code, install the (GitHub Actions) exstension and you will be able to push/pull from inside of visual stuido code.

***

- Run to switch between git branches
```
git switch benjamin
```

***