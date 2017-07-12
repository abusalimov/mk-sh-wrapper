SELF_DIR := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))
$(warning ^^^)