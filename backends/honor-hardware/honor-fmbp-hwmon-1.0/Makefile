obj-m := honor-fmbp-hwmon.o
KVER ?= $(shell uname -r)
KDIR ?= /lib/modules/$(KVER)/build
KERNEL_LLVM := $(shell grep -q '^CONFIG_CC_IS_CLANG=y' $(KDIR)/.config 2>/dev/null && echo 1)
LLVM_ARG := $(if $(KERNEL_LLVM),LLVM=1)
all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) $(LLVM_ARG) modules
clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
