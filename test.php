<?php

//=========================================================================================================
// File:        test.php
// Case:        VUT, FIT, IPP, project
// Date:        7. 3. 2021
// Author:      David Mihola
// Contac:      xmihol00@stud.fit.vutbr.cz
// Interpreted: PHP 7.4.3 (cli) (built: Oct  6 2020 15:47:56) ( NTS )   
// Description: Test script for the parser.php and interpret.py scripts.
//==========================================================================================================

ini_set('display_errors', 'stderr');

// ===================================== constant definitions ======================================

define("INTERNAL_ERR", 99);
define("ARG_ERR", 10);
define("IN_FILE_ERR", 11);
define("OUT_FILE_ERR", 12);
define("DIR_FILE_ERR", 41);
define("FILE_EXT", "/(\.src|\.in|\.out|\.rc)$/");
define("PARSER", 0b1);
define("INTERPRET", 0b10);
define("BOTH", 0b11);
define("PHP_COMMAND", "php7.4 ");
define("PYTHON_COMMAND", "python3.8 ");

const arguments = array("help", "directory:", "recursive", "parse-script:", "int-script:", "parse-only", "int-only",
                        "jexamxml:", "jexamcfg:");

// =================================== end constant definitions ====================================

// ============================================ classes ============================================

class Arguments
{
    public $directory;
    public $recursive;
    public $parser;
    public $interpret;
    public $test_type;
    public $xml_comparer;
    public $xml_options;

    public function __construct()
    {
        $this->directory = "./";
        $this->recursive = false;
        $this->parser = "parse.php";
        $this->interpret = "interpret.py";
        $this->test_type = BOTH;
        $this->xml_comparer = "/pub/courses/ipp/jexamxml/jexamxml.jar";
        $this->xml_options = "/pub/courses/ipp/jexamxml/options";
    }
}

// ========================================= end of classes ========================================

// ========================================== program body =========================================

$args = new Arguments();
parse_program_arguments($argc);

$groups = create_file_groups($args->directory, $args->recursive); 

$test_tree = generate_missing_files($groups, $args->directory);

$results[substr($args->directory, 0, -1)] = run_test($test_tree, $args->directory);

create_HTML_output($results);

// ====================================== end of program body ======================================

// =========================================== functions ===========================================

/**
 * @brief Parses the program arguments. Exits with error, when the arguments are incorrect (10) or when the specified
 *        files does not exist or cannot be accessed (11).
 * @param argc the number of arguments. 
 **/
function parse_program_arguments($argc)
{
    global $args;
    $options = getopt("", arguments);
    
    if ($options === false || count($options) < $argc - 1)
    {
        exit(ARG_ERR);
    }

    if ($argc == 2 && array_key_exists("help", $options))
    {
        print_help_msg();
        exit(0);
    }

    foreach ($options as $key => $value)
    {
        switch ($key)
        {
            case "directory":
                if (substr($value, -1) != '/')
                {
                    $args->directory = $value . "/";    
                }
                else
                {
                    $args->directory = $value;
                }
                break;

            case "recursive":
                $args->recursive = true;
                break;

            case "parse-script":
                if ($args->test_type == INTERPRET)
                {
                    exit(ARG_ERR);
                }
                $args->parser = $value;
                break;
            
            case "int-script":
                if ($args->test_type == PARSER)
                {
                    exit(ARG_ERR);
                }
                $args->interpret = $value;
                break;
            
            case "int-only":
                if ($args->test_type == PARSER || array_key_exists("parse-script", $options))
                {
                    exit(ARG_ERR);
                }
                $args->test_type = INTERPRET;
                break;
            
            case "parse-only":
                if ($args->test_type == INTERPRET || array_key_exists("int-script", $options))
                {
                    exit(ARG_ERR);
                }
                $args->test_type = PARSER;
                break;

            case "jexamxml":
                $args->xml_comparer = $value;
                break;
            
            case "jexamcfg":
                $args->xml_options = $value;
                break;
            
            default:
                exit(ARG_ERR);
        }
    }

    if (!is_readable($args->directory) || !is_dir($args->directory))
    {
        exit(DIR_FILE_ERR);
    }
    if ($args->test_type & INTERPRET && (!is_readable($args->interpret) || !is_file($args->interpret)))
    {
        exit(DIR_FILE_ERR);
    }
    if ($args->test_type & PARSER && (!is_readable($args->parser) || !is_file($args->parser)))
    {
        exit(DIR_FILE_ERR);
    }
    if (!is_readable($args->xml_comparer) || !is_file($args->xml_comparer))
    {
        exit(DIR_FILE_ERR);
    }
    if (!is_readable($args->xml_options) || !is_file($args->xml_options))
    {
        exit(DIR_FILE_ERR);
    }

    return $args;
}

/**
 * @brief Loads paths and file names used for testing to a multidimensional array.
 * @param path the path to a starting directory, where test files are to be found.
 * @param recursive true when the search for test files is recursive.
 * @return array a multidimensional array of groups of files, which were evaluated as test files.
 **/
function create_file_groups($path, $recursive)
{
    $groups = array();
    $dir = scandir($path);
    foreach ($dir as $file)
    {
        if (!is_readable($path . $file))
        {
            if (preg_match(FILE_EXT, $path . $file))
            {
                exit(IN_FILE_ERR);
            }
            else if (filetype($path . $file) == "dir")
            {
                exit(DIR_FILE_ERR);
            }
            else
            {
                continue;
            }
        }

        if (filetype($path . $file) == "file" && preg_match(FILE_EXT, $file))
        {
            $trimmed = substr($file, 0, strpos($file . ".", "."));
            if (!array_key_exists($trimmed, $groups))
            {
                $groups[$trimmed] = array();
            }
            array_push($groups[$trimmed], $file);
        }
        else if ($recursive && $file != "." && $file != ".." && filetype($path . $file) == "dir")
        {
            $groups[$file] = create_file_groups($path . $file . "/", true);
        }
    }
    return $groups;
}

/**
 * @brief Generates missing test files from loaded test groups, simplyfies the test structure 
 *        by stripping the file suffixes and keeping just the name of the test case.
 * @param file_groups multidimensional array tree of loaded files, each node containing one file group, which can be incomplete.
 * @return array multidimensional array tree of the names of the test file groups - test cases. 
 **/
function generate_missing_files(&$file_groups, $path)
{
    $test_tree[$path] = array();
    foreach ($file_groups as $key => $group)
    {
        foreach($group as $file)
        {
            if (is_array($file))
            {
                $files = generate_missing_files($group, $path . $key . "/");
                if (!in_array($files, $test_tree[$path]))
                {
                    array_push($test_tree[$path], $files);
                }
            }
        }

        if (array_search($key . ".src", $group) !== false)
        {
            array_push($test_tree[$path], $key);

            if (array_search($key . ".in", $group) === false)
            {
                $file = fopen($path . $key . ".in", 'w');
                if ($file === false)
                {
                    exit(IN_FILE_ERR);
                }
                fclose($file);
            }
            if (array_search($key . ".out", $group) === false)
            {
                $file = fopen($path . $key . ".out", 'w');
                if ($file === false)
                {
                    exit(IN_FILE_ERR);
                }
                fclose($file);
            }
            if (array_search($key . ".rc", $group) === false)
            {
                $file = fopen($path . $key . ".rc", 'w');
                if ($file === false)
                {
                    exit(IN_FILE_ERR);
                }
                fwrite($file, "0");
                fclose($file);
            }
        }
    }

    return $test_tree;
}

/**
 * @brief Runs the given test either on both parser and parser, or separately if specified. 
 * @param test_cases multidimensional array tree of the names of the test file groups. 
 *                   Name of the group is determined by stripping the suffixes from a group of test files.
 * @return array multidimensional array of the tests results. Dimension is determined by the tested file structure.
 **/
function run_test($test_cases)
{
    global $args;
    $path = key($test_cases);
    $test_results = array();
    foreach ($test_cases[$path] as $test)
    {
        if (is_array($test))
        {
            $test_results[substr(key($test), 0, -1)] = run_test($test);
        }
        else
        {
            $output = false;
            if ($args->test_type & PARSER)
            {
                $output = run_parser($path . $test);
                if ($output[0])
                {
                    $test_results[$test] = true;
                    if ($output[1] === false)
                    {
                        continue;
                    }
                    $output = $output[1];
                }
                else
                {
                    $test_results[$test] = false;
                    continue;
                }
            }

            if ($args->test_type & INTERPRET)
            {
                if (run_interpret($path . $test, $output))
                {
                    $test_results[$test] = true;
                }
                else
                {
                    $test_results[$test] = false;
                }
            }
        }
    }
    return $test_results;
}

/**
 * @brief Tests the parser on a specific test case
 * @param test the path and name of the test file group without the file suffix
 * @return array(bool, string) true and the parser xml output on success, otherwise false and a empty string.
 **/
function run_parser($test)
{
    global $args;

    $descriptors = array(array("pipe", "r"), array("pipe", "w"));

    $process = proc_open(PHP_COMMAND . $args->parser, $descriptors, $pipes);

    if (is_resource($process))
    {

        fwrite($pipes[0], file_get_contents($test . ".src"));
        fclose($pipes[0]);

        $output = stream_get_contents($pipes[1]);
        fclose($pipes[1]);

        $ret_val = proc_close($process);
    }

    $rc = trim(file_get_contents($test . ".rc"));
    if (!is_numeric($rc))
    {
        return array(false, "");
    }
    $rc = (int)$rc;

    if ($ret_val != $rc && $ret_val != 0)
    {
        return array(false, "");
    }
    else if ($args->test_type == PARSER && $ret_val == 0 && $rc == 0)
    {
        $file = tmpfile();
        if ($file === false)
        {
            exit(DIR_FILE_ERR);
        }
        $tmp_path = stream_get_meta_data($file)['uri'];
        fwrite($file, $output);
        fseek($file, 0);
        
        exec("java -jar " . $args->xml_comparer . " " . $tmp_path . " " . $test . ".out" . " /dev/null " . $args->xml_options, $arr_out, $ret_val);
        fclose($file);
        
        return array(!$ret_val, " ");
    }
    else if ($args->test_type == BOTH && $ret_val == 0)
    {
        return array(true, $output);
    }
    else if ($ret_val == $rc)
    {
        return array(true, false);
    }
    else
    {
        return array(false, "");
    }
}

/**
 * @brief Tests the interpret on a specific test case
 * @param test the path and name of the test file group without the file suffix
 * @param input string with the output of the parser, or false, when parser was not used.
 * @return boolean true on successful testcase, otherwise false
 **/
function run_interpret($test, $input)
{
    global $args;

    if ($input === false)
    {
        $input = file_get_contents($test . ".src");
        if ($input === false)
        {
            exit(IN_FILE_ERR);
        }
    }

    $descriptors = array(array("pipe", "r"), array("pipe", "w"));

    $process = proc_open(PYTHON_COMMAND . $args->interpret . " --input=" . $test . ".in 2>/dev/null", $descriptors, $pipes);

    if (is_resource($process))
    {
        fwrite($pipes[0], $input);
        fclose($pipes[0]);

        $output = stream_get_contents($pipes[1]);
        fclose($pipes[1]);

        $ret_val = proc_close($process);
    }
    else
    {
        exit(INTERNAL_ERR);
    }

    $rc = trim(file_get_contents($test . ".rc"));
    if (!is_numeric($rc))
    {
        return array(false, "");
    }
    $rc = (int)$rc;

    if ($ret_val != $rc)
    {
        return false;
    }
    if ($ret_val == 0)
    {
        $file = tmpfile();
        if ($file === false)
        {
            exit(DIR_FILE_ERR);
        }
        $tmp_path = stream_get_meta_data($file)['uri'];
        fwrite($file, $output);
        fseek($file, 0);
        
        exec("diff -s " . $tmp_path . " " . $test . ".out", $arr_out, $ret_val);
        fclose($file);
        return !$ret_val;
    }

    return true;
}

/**
 * @brief Generates the HTML output to STDOUT.
 * @param results the result tree of proceeded test (in case of recursive testing of a directory) or an array of results.
 **/
function create_HTML_output($results)
{
    echo "<!DOCTYPE html>\n";
    echo "<html>\n";

        echo "\t<head>\n";
            echo "\t\t<title>Test Results</title>\n";
        echo "\t</head>\n";
        
        echo "\t<body style=\"padding-left: 5%\">\n";
            echo "<h1>Results</h1>\n";
            echo "Press the arrow icon to view details.\n";
            echo "\t\t<ul id=\"tests\">\n";
            $res = format_results_to_HTML($results, "\t\t\t");
            $total = $res[0] + $res[1];
            echo "\t\t</ul>\n";
            echo "<h2 style=\"margin-top: 50px\">Overall summary</h2>\n";
            echo "<h3>Tests run: " . $total . "</h3>\n";
            echo "<h3 class=\"success\">Passed: " . $res[0] . "</h3>\n";
            echo "<h3 class=\"failure\">Failed: " . $res[1] . "</h3>\n";
        echo "\t</body>\n";

        add_CSS();
        add_JS();
    echo "</html>\n";
}

/**
 * @brief Formats the result tree and prints it to STDOUT in a HTML format.
 * @param results the result tree (in case of recursive testing of a directory) or an array of results.
 * @param indent indent of printed lines to ensure easy readability of the generated output.
 **/
function format_results_to_HTML($results, $indent)
{
    $failed = 0;
    $succeded = 0;
    foreach($results as $key => $result)
    {
        if(is_array($result))
        {
            echo $indent . "<li><span class=\"arrow\">direcotry: <b>" . $key . "</b> | </span>\n";
                echo $indent . "\t<ul class=\"hidden\">\n";
                $res = format_results_to_HTML($result, $indent . "\t\t");
                $succeded += $res[0];
                $failed += $res[1];
                echo $indent . "\t</ul>\n";
            echo $indent . "summary: <span class=\"success\">PASSED: </span>" . $res[0] . "  <span class=\"failure\">FAILED: </span>" . $res[1] . "</li>\n";
        }
        else
        {
            if ($result)
            {
                echo $indent . "<li>- test case: <b>". $key . "</b> -> " . "<span class=\"success\">PASSED</span>" . "</li>\n";
                $succeded++;
            }
            else
            {
                echo $indent . "<li>- test case: <b>" . $key . "</b> -> " . "<span class=\"failure\">FAILED</span>" . "</li>\n";
                $failed++;
            }
        }
    }

    return array($succeded, $failed);
}

/**
 * @brief Prints needed CSS for styling the HTML output to STDOUT.
 **/
function add_CSS()
{
    echo "\t<style>\n";

        echo "\tul {\n"; 
        echo "\t\tlist-style-type: none;\n";
        echo "\t}\n\n";

        echo "\t.arrow {\n";
        echo "\t\tcursor: pointer;\n";
        echo "\t\tuser-select: none;\n";
        echo "\t}\n\n";

        echo "\t.arrow::before {\n";
        echo "\t\tcontent: \"\\25B6\";\n";
        echo "\t\tcolor: black;\n";
        echo "\t\tdisplay: inline-block;\n";
        echo "\t\tmargin-right: 6px;\n";
        echo "\t}\n\n";

        echo "\t.arrow-closed::before {\n";
        echo "\t\ttransform: rotate(90deg);\n";
        echo "\t}\n\n";

        echo "\t.hidden {\n";
        echo "\t\tdisplay: none;\n";
        echo "\t}\n\n";

        echo "\t.shown {\n";
        echo "\t\tdisplay: block;\n";
        echo "\t}\n";
        
        echo "\t.success {\n";
        echo "\t\tcolor: green;\n";
        echo "\t\tfont-weight: bold;";
        echo "\t}\n";

        echo "\t.failure {\n";
        echo "\t\tcolor: red;\n";
        echo "\t\tfont-weight: bold;";
        echo "\t}\n";

    echo "\t</style>\n";
}

/**
 * @brief Prints JavaScript function adding interactive functionality to the generated HTML output to STDOUT.
 **/
function add_JS()
{
    echo "\t<script>\n";
        echo "\t\tvar toggle = document.getElementsByClassName(\"arrow\");\n\n";
        echo "\t\tfor (var i = 0; i < toggle.length; i++)\n";
        echo "\t\t{\n";
        echo "\t\t\ttoggle[i].addEventListener(\"click\", function()\n";
        echo "\t\t\t{\n";
        echo "\t\t\t\tthis.parentElement.querySelector(\".hidden\").classList.toggle(\"shown\");\n";
        echo "\t\t\t\tthis.classList.toggle(\"arrow-closed\");\n";
        echo "\t\t\t});\n";
        echo "\t\t}\n";
    echo "\t</script>\n";
}

/**
 * @brief Prints the help message to STDOUT.
 **/
function print_help_msg()
{
    echo "Usage: test.php [option] ...\n";
    echo "Options:\n";
    echo "--help \t\t\tDisplay help message.\n";
    echo "--directory=<path> \tSearches for test files in a directroy <path>.\n";
    echo "--recursive \t\tSearches the tested directory recursively.\n";
    echo "--parse-script=<file> \tUses parser script <file> written in PHP 7.4. Cannot be combined with option --int-only.\n";
    echo "--int-script=<file> \tUses interpret script <file> written in Python 3.8. Cannot be combined with option --parse-only.\n";
    echo "--parse-only \t\tPerforms tests only on the parser. Cannot be combined with options --int-only and --int-script=<file>.\n";
    echo "--int-only \t\tPerforms tests only on the interpret. Cannot be combined with options --parse-only and --parse-script=<file>.\n";
    echo "--jexamxml=<file> \tJAR file <file> with the XML comparison tool A7Soft JExamXML.\n";
    echo "--jexamcfg=<file> \tFile <file> with the configurations of the XML comparison tool A7Soft JExamXML.\n";
}

// ======================================== end of functions =======================================

?>