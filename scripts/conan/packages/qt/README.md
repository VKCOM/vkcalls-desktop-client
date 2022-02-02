## Как собрать Qt с нашими патчами

В данной инструкции используются следующие инструменты: \
[Python 3](python.org) \
[Conan package manager](conan.io) 

Мы предполагаем, что Вы уже знакомы с основами Conan. \
С документацией можно ознакомиться по ссылке: \
[docs.conan.io](docs.conan.io)

Для сборки мы используем рецепт и исходники Qt 5.15.2 из репозитория center.conan.io. \
На исходники накладываются патчи из каталога **patches**. \
На conanfile.py накладываются патчи из каталога **conanfile-patches**. Эти пачти нужны для работы нашего скрипта сборки **qt/conan-create.py**.

### 1 Подготовка

#### 1.0 Перейти в директорию Qt

```
cd ${VKCALLS_REPOSITORY_ROOT}/scripts/conan/packages/qt/
```

#### 1.1 Установить Conan

```
python3 -m pip install conan
conan config init
```

#### 1.2 Добавить conancenter remote

##### 1.2.1 Очистить remotes (Опционально)

```
conan remote clean
```

##### 1.2.2 Добавить conancenter remote

```
conan remote add --insert 0 --force conancenter https://center.conan.io true
```

#### 1.3 Установить зависимости Python

##### 1.3.1 Создать новое виртуальное окружение (опционально)
```
python3 -m venv vkcalls
source vkcalls/bin/activate
```

##### 1.3.2 Установить зависимости
```
python3 -m pip install -r requirements.txt
```

#### 2 Запустить Сборку

```
python3 conan-create.py
```

#### 3 Собранную библиотеку можно найти тут:

```
${USER_HOME_DIR}/.conan/data/qt/5.15.2-p1/vkcalls/stable/package/
```

#### 4. Помощь

```
python3 conan-create.py --help
```
