# Test to delete dir tree with many files inside


## 1. Create slow file system into `slowfs` dir
	```shell
		./mount-slowfs.sh slowfs
	```
	
## 2. Generate dirs tree with many files inside
	```shell
		./create-test-tree.sh slowfs/test_dir
	```

## 3. Launch QuickFile file manager and execute delete `slowfs` directory with DISABLED "move to trash" option.

	```shell
		python main.py
	```

## Unmount slow file system
	```shell
		./unmount-slowfs.sh slowfs
	```



### Note

I haven't noticed any benefit from using 'word'. However, I will add that there are ways for additional &quot;indirect&quot; slowdown of this file system.
