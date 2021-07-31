#!/bin/bash

php7.4 test.php --recursive --parse-only --directory=tests/parse_only >test_results/parse_only.html
php7.4 test.php --recursive --parse-only --directory=FIT_tests/parse-only >test_results/FIT_parse_only.html

php7.4 test.php --recursive --int-only --directory=tests/int_only >test_results/int_only.html
php7.4 test.php --recursive --int-only --directory=FIT_tests/interpret-only >test_results/FIT_int_only.html

php7.4 test.php --recursive --directory=tests/both >test_results/both.html
php7.4 test.php --recursive --directory=FIT_tests/both >test_results/FIT_both.html
