<?php

//=========================================================================================================
// File:        parse.php
// Case:        VUT, FIT, IPP, project
// Date:        16. 2. 2021
// Author:      David Mihola
// Contac:      xmihol00@stud.fit.vutbr.cz
// Interpreted: PHP 7.4.3 (cli) (built: Oct  6 2020 15:47:56) ( NTS )   
// Description: XML parser of the IPPcode21 intemidiate language
//==========================================================================================================

// ========================================== error codes ==========================================

ini_set('display_errors', 'stderr');

define("HEADER_ERR", 21);
define("INSTRUCTION_ERR", 22);
define("LEX_SYN_ERR", 23);
define("ARG_ERR", 10);
define("INTERNAL_ERR", 99);
define("OUT_FILE_ERR", 12);

// ====================================== end of error codes =======================================

// ======================================= regex definitions =======================================

define("PROG_HEADER", "/^(\.IPPcode21|\.IPPcode21(\t|\s)*#.*)$/i");
define("LINE_SPLIT", "/\s+/");
define("ARGS", "/^--(loc|comments|labels|jumps|fwjumps|backjumps|badjumps)$/");
define("HELP_ARG", "/^--help$/");
define("STATS_ARG", "/^--stats=/");
define("NONE", "/^(CREATEFRAME|PUSHFRAME|POPFRAME|RETURN|BREAK)$/i");
define("NONE_COMMENT", "/^(CREATEFRAME|PUSHFRAME|POPFRAME|RETURN|BREAK)#.*$/i");
define("RET", "/^RETURN$/i");
define("SVAR", "/^(DEFVAR|POPS)$/i");
define("LBL", "/^LABEL$/i");
define("JUMP", "/^(CALL|JUMP)$/i");
define("SYMB", "/^(DPRINT|EXIT|WRITE|PUSHS)$/i");
define("VAR_SYMB", "/^(MOVE|INT2CHAR|STRLEN|TYPE|NOT)$/i");
define("VAR_TYPE", "/^READ$/i");
define("VAR_SYMB_SYMB", "/^(ADD|SUB|MUL|IDIV|STRI2INT|CONCAT|GETCHAR|SETCHAR|LT|GT|EQ|AND|OR)$/i");
define("LABEL_SYMB_SYMB", "/^(JUMPIFEQ|JUMPIFNEQ)$/i");
define("COMMENT", "/^#.*/i");
define("VARIABLE", "/^(GF|TF|LF)@([A-Za-z_\-$&%*!?])([A-Za-z0-9_\-$&%*!?])*$/");
define("INTGR", "/^int@.*$/");
define("BOOLN", "/^bool@(true|false)$/");
define("NIL", "/^nil@nil$/");
define("LABEL", "/^([A-Za-z_\-$&%*!?])([A-Za-z_0-9_\-$&%*!?])*$/i");
define("TYPE", "/^(int|bool|string)$/");
define("STR_ESCAPE", "/^[0-9][0-9][0-9]/");

// ==================================== end of regex definitions ===================================

// ============================================ classes ============================================

/** 
 * @class Parses the command line arguments used for statistics, cellects the statistics during parsing,
 *        writes the desired statistics to specified files.  
 **/
class Statistics
{
    private $loc;
    private $comments;
    private $labels;
    private $jumps;
    private $fwjumps;
    private $backjumps;
    private $badjumps;
    private $label_names;
    private $unknown_labels;
    private $stats_active;
    private $stats_args;
    private $partial_stats;
    private $files;

    public function __construct()
    {
        $this->loc = 0;
        $this->comments = 0;
        $this->labels = 0;
        $this->jumps = 0;
        $this->fwjumps = 0;
        $this->backjumps = 0;
        $this->badjumps = 0;
        $this->label_names = array();
        $this->unknown_labels = array();
        $this->stats_active = false;
        $this->stats_args = array();
        $this->partial_stats = array();
        $this->files = array();
    }

    /**
     * @brief Increases the number of parsed instructions. 
     **/
    public function add_inst()
    {
        return ++$this->loc;
    }

    /**
     * @brief Increases the number of parsed comments. 
     **/
    public function add_comment()
    {
        return ++$this->comments;
    }

    /**
     * @brief Increases the number of parsed labels, and collects them. 
     **/
    public function add_label($label)
    {
        $this->labels++;
        array_push($this->label_names, $label);
        while (($index = array_search($label, $this->unknown_labels)) !== false)        
        {
            unset($this->unknown_labels[$index]); // correct forward jump
        }
    }

    /**
     * @brief Increases the number of parsed jumps, including forward jumps, backward jumps and bad jumps
     *        based on collected labels. 
     **/
    public function add_jump($label)
    {
        $this->jumps++;
        $index = array_search($label, $this->label_names);

        if ($index === false)
        {
            array_push($this->unknown_labels, $label);
            
            $this->fwjumps++; // label not defined yet, therfore forward or bad jump
        }
        else
        {
            $this->backjumps++; // label already defined, therfore backward jump
        }
    }

    /**
     * @brief Increases the number of parsed jumps, but does not calculate forward, backward and bad jumps. 
     **/
    public function add_return()
    {
        $this->jumps++;
    }

    /**
     * @brief Parses the command line arguments used for collecting statistics.
     *        When parsing is unsuccessful, exits with error code 10 on an invalid command line
     *        argument or 12 on an invalid file specification (i. e. filename is not specified).
     * @param argc the number of command line arguments
     * @param argv the command line arguments 
     **/
    public function parse_arguments($argc, $argv)
    {
        for ($i = 1; $i < $argc; $i++)
        {
            if (preg_match(STATS_ARG, $argv[$i]))
            {
                if ($this->stats_active)
                {
                    array_push($this->stats_args, $this->partial_stats);
                }
                $this->stats_active = true;
                $this->partial_stats = array();
                $file_name = substr($argv[$i], 8);
                if (strlen($file_name) == 0)
                {
                    exit(ARG_ERR); //not entered filename
                }

                array_push($this->partial_stats, $file_name);
                if (array_search($file_name, $this->files) !== false)
                {
                    exit(OUT_FILE_ERR); // file was already used for different statistics set
                }
                else
                {
                    array_push($this->files, $file_name);
                }
            }
            else if (preg_match(ARGS, $argv[$i]) && $this->stats_active)
            {
                array_push($this->partial_stats, substr($argv[$i], 2));
            }
            else
            {
                exit(ARG_ERR); // wrong argument
            }
        }

        if ($this->stats_active)
        {
            array_push($this->stats_args, $this->partial_stats);
        }
    }

    /**
     * @brief Writes the desired collected statistics in to specified files. Exits with error code 12,
     *        when specified file cannot be accessed. 
     **/
    public function write_to_files()
    {
        foreach($this->stats_args as $stat)
        {
            $file = fopen($stat[0], 'w');
            if ($file)
            {
                foreach($stat as $attrib)
                {
                    switch($attrib)
                    {
                        case "loc": // number of instructions
                            fwrite($file, $this->loc . "\n");                          
                            break;
                        
                        case "comments": // number of comments
                            fwrite($file, $this->comments . "\n");
                            break;
                        
                        case "labels": // number of labels
                            fwrite($file, $this->labels . "\n");
                            break;

                        case "jumps": // number of jumps
                            fwrite($file, $this->jumps . "\n");
                            break;
                        
                        case "fwjumps": // number of forward jumps
                            // bad jumps are subtracted
                            fwrite($file, $this->fwjumps - sizeof($this->unknown_labels) . "\n");
                            break;
                        
                        case "backjumps": // number of backward jumps
                            fwrite($file, $this->backjumps . "\n");
                            break;
                        
                        case "badjumps": // number of bad jumps
                            fwrite($file, sizeof($this->unknown_labels) . "\n");
                            break;
                    }
                }
            }
            else
            {
                exit(OUT_FILE_ERR);
            }

            fclose($file);
        }
    }
}

/** 
 * @class Builds and prints the script output in the XML format from the parsed source code.
 **/
class XML_builder
{
    private $body;
    private $program;
    private $instruction;
    private $inst_counter;
    private $arg_counter;

    public function __construct()
    {
        $this->inst_counter = 0;
        $this->arg_counter = 0;
        $this->body = new DOMdocument("1.0", "UTF-8");
        $this->body->formatOutput = true;
        $this->program = $this->body->createElement("program");
        $this->program->setAttribute("language", "IPPcode21");
        $this->body->appendChild($this->program);
    }

    /**
     * @brief Creates a new instruction and assigns it with the correct order. 
     **/
    public function create_instruction()
    {
        $this->instruction = $this->body->createElement("instruction");
        $this->program->appendChild($this->instruction);
        $this->instruction->setAttribute("order", ++$this->inst_counter);
        $this->arg_counter = 0;
    }

    /**
     * @brief Adds an instruction opcode to a newly created instruction.
     * @warning The function can be used only once after the function @relates create_instruction().
     * @param opcode the opcode to be added to the instruction.
     **/
    public function add_instruction_opcode($opcode)
    {
        $this->instruction->setAttribute("opcode", strtoupper($opcode));
    }

    /**
     * @brief Adds an instruction argument with correct order to a currently created instruction.
     * @warning Instruction must be created before this functions is called by calling @relates add_instruction_opcode($opcode).
     * @param arg the value of the argument.
     * @param type the type of the argument.
     **/
    public function add_intsruction_argument($arg, $type)
    {
        $arg = $this->body->createElement("arg" . ++$this->arg_counter, $this->convert_xml_characters($arg));
        $this->instruction->appendChild($arg);
        $arg->setAttribute("type", $type);
    }

    /**
     * @brief Writes the XML representation of a source code to STDOUT.
     **/
    public function write_to_stdout()
    {
        echo $this->body->saveXML();
    }

    /**
     * @brief Converts special XML characters to their XML escape sequences.
     * @param str the string to be converted.
     * @return string the converted string. 
     **/
    private function convert_xml_characters($str)
    {
        return str_replace(array("&", ">", "<", "\"", "'"), array("&amp;", "&gt;", "&lt;", "&quot;", "&apos;"), $str);
    }
}

// ========================================= end of classes ========================================

// ========================================== program body =========================================

// statistics collector
$stats = new Statistics();

if ($argc == 2 && preg_match(HELP_ARG, $argv[1]))
{ 
    // print help message and exit the program successfuly
    print_help_msg();
    exit(0);
}

// parsing of arguments other than help message, ends with error, if a help argument is included.
$stats->parse_arguments($argc, $argv);

// check that the source file has a correct header
check_src_header();

$xml_file = new XML_builder();

// parse the source code line by line
while($line = fgets(STDIN))
{
    parse_line($line);
}

// write the statistics to desired files
$stats->write_to_files();

// write the XML output to STDOUT
$xml_file->write_to_stdout();

// ====================================== end of program body ======================================

// =========================================== functions ===========================================

/**
 * @brief Checks that the source file from STDIN has a corect header (.IPPcode21).
 *        Exits with error 21, when the header is missing or is incorrect.
 **/
function check_src_header()
{
    global $stats;
    $found = false;
    while($line = fgets(STDIN))
    {
        $line = trim($line);
        if (strlen($line) != 0)
        {
            if (preg_match(PROG_HEADER, $line))
            {
                $found = true;
                if (strpos($line, '#') !== false)
                {
                    $stats->add_comment();
                }
                break; // header found
            }
            else if (preg_match(COMMENT, $line))
            {
                $stats->add_comment();
            }
            else
            {
                exit(HEADER_ERR); // incorrect header
            }
        }
    }
    
    if (!$found)
    {
        exit(HEADER_ERR);
    }
}

/**
 * @brief Parses a line of the given source code. The line is splitted to an array of separate lexemes, 
 *        with which oder auxiliary functions are called to perform the task effectively.
 *        Exits with error 22 when invalid instruction code is encountered or with error 22 when the source code
 *        is not lexicaly or semantically correct.
 * @param line the line to be parsed. 
 **/
function parse_line($line)
{
    global $stats, $xml_file;
    $line = trim($line);
    $lexemes = preg_split(LINE_SPLIT, $line); // split the line to lexemes
    if (strlen($lexemes[0]) > 0)
    {
        if (preg_match(COMMENT, $lexemes[0]))
        {
            // line with comment
            $stats->add_comment();
            return;
        }

        $stats->add_inst();
        $xml_file->create_instruction();
        
        if (preg_match(VAR_SYMB_SYMB, $lexemes[0]))
        {
            // instruction followed by varibale, symbol and symbol
            parse_VSS($lexemes);
        }
        else if (preg_match(NONE, $lexemes[0]))
        {
            // instrction not followed by variable nor symbol nor type...
            if (sizeof($lexemes) > 1)
            {
                $stats->add_comment();
                if (substr($lexemes[1], 0, 1) != "#")
                {
                    exit(LEX_SYN_ERR);
                }
            }
            $xml_file->add_instruction_opcode($lexemes[0]);
            if (preg_match(RET, $lexemes[0]))
            {
                $stats->add_return(); // add return to statistics
            }
        }
        else if (preg_match(NONE_COMMENT, $lexemes[0]))
        {
            // instrction not followed by variable nor symbol nor type, with directly folloeing comment
            $stats->add_comment();
            $lexemes[0] = substr($lexemes[0], 0, strpos($lexemes[0], "#"));
            $xml_file->add_instruction_opcode($lexemes[0]);
            if (preg_match(RET, $lexemes[0]))
            {
                $stats->add_return(); // add return to statistics
            }
        } 
        else if (preg_match(VAR_SYMB, $lexemes[0]))
        {
            // instruction followed by varibale and symbol
            parse_VS($lexemes);
        }
        else if (preg_match(SYMB, $lexemes[0]))
        {
            // instruction followed by symbol
            parse_S($lexemes);
        }
        else if (preg_match(SVAR, $lexemes[0]))
        {
            // instruction followed by varibale
            parse_V($lexemes);
        }
        else if (preg_match(LABEL_SYMB_SYMB, $lexemes[0]))
        {
            // instruction followed by label, symbol and symbol
            parse_LSS($lexemes);
        }
        else if (preg_match(LBL, $lexemes[0]))
        {
            // instruction followed by label
            parse_L($lexemes);
        }
        else if (preg_match(JUMP, $lexemes[0]))
        {
            // jump instruction followed by label
            parse_LJ($lexemes);
        }
        else if (preg_match(VAR_TYPE, $lexemes[0]))
        {
            // instruction followed by varibale and type
            parse_VT($lexemes);
        }
        else
        {
            exit(INSTRUCTION_ERR); // unknown instruction
        }
    }
    else if (sizeof($lexemes) > 1)
    {
        exit(LEX_SYN_ERR);
    }
}

/**
 * @brief Parses an array of lexemes following an instruction, which is supposed to be followed by variable, symbol and symbol.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_VSS($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 4)
    {
        if (parse_variable($lexemes[1]))
        {
            exit(LEX_SYN_ERR); // variable followed by an unexpected comment
        }
        if (parse_symbol($lexemes[2]))
        {
            exit(LEX_SYN_ERR); // symbol followed by an unexpected comment
        }
        if (($ret = parse_symbol($lexemes[3])) || sizeof($lexemes) > 4)
        {
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 4 && !(substr($lexemes[4], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 4 lexemes without a comment
        }
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for a given instruction
    }
}

/**
 * @brief Parses an array of lexemes following an instruction (included), which is supposed to be followed by variable and symbol.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_VS($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 3)
    {
        if (parse_variable($lexemes[1]))
        {
            exit(LEX_SYN_ERR); // variable followed by an unexpected comment
        }
        if (($ret = parse_symbol($lexemes[2])) || sizeof($lexemes) > 3)
        {
            // variable is directly followed by a comment or there are more than 3 lexemes, which have to result
            // in comment, if the source code is correct.
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 3 && !(substr($lexemes[3], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 3 lexemes without a comment
        }
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for a given instruction
    }
}

/**
 * @brief Parses an array of lexemes following an instruction (included), which is supposed to be followed by a symbol.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_S($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 2)
    {
        if (($ret = parse_symbol($lexemes[1])) || sizeof($lexemes) > 2)
        {
            // variable is directly followed by a comment or there are more than 2 lexemes, which have to result
            // in comment, if the source code is correct.
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 2 && !(substr($lexemes[2], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 2 lexemes without a comment
        }
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for a given instruction
    }
}

/**
 * @brief Parses an array of lexemes following an instruction (included), which is supposed to be followed by a variable.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_V($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 2)
    {
        if (($ret = parse_variable($lexemes[1])) || sizeof($lexemes) > 2)
        {
            // variable is directly followed by a comment or there are more than 2 lexemes, which have to result
            // in comment, if the source code is correct.
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 2 && !(substr($lexemes[2], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 2 lexemes without a comment
        }
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for a given instruction
    }
}

/**
 * @brief Parses an array of lexemes following an instruction (included), which is supposed to be followed by label, symbol and symbol.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_LSS($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 4)
    {
        if (parse_label($lexemes[1]))
        {
            exit(LEX_SYN_ERR); // label followed by an unexpected comment
        }
        if (parse_symbol($lexemes[2]))
        {
            exit(LEX_SYN_ERR); // symbol followed by an unexpected comment
        }
        if (($ret = parse_symbol($lexemes[3])) || sizeof($lexemes) > 4)
        {
            // variable is directly followed by a comment or there are more than 4 lexemes, which have to result
            // in comment, if the source code is correct.
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 4 && !(substr($lexemes[4], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 4 lexemes without a comment
        }
        $stats->add_jump($lexemes[1]);
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for a given instruction
    }
}

/**
 * @brief Parses an array of lexemes following an instruction, which is supposed to be followed by a label.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_L($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 2)
    {
        if (($ret = parse_label($lexemes[1])) || sizeof($lexemes) > 2)
        {
            // variable is directly followed by a comment or there are more than 2 lexemes, which have to result
            // in comment, if the source code is correct.
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 2 && !(substr($lexemes[2], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 2 lexemes without a comment
        }
        $stats->add_label($lexemes[1]);
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for a given instruction
    }
}

/**
 * @brief Parses an array of lexemes following an instruction, which is supposed to be followed by an uncoditioned jump.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_LJ($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 2)
    {
        if (($ret = parse_label($lexemes[1])) || sizeof($lexemes) > 2)
        {
            // variable is directly followed by a comment or there are more than 2 lexemes, which have to result
            // in comment, if the source code is correct.
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 2 && !(substr($lexemes[2], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 2 lexemes without a comment
        }
        $stats->add_jump($lexemes[1]);
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for a given instruction
    }
}

/**
 * @brief Parses an array of lexemes following an instruction, which is supposed to be followed by variable and type.
 *        Correct comments are ignored.
 *        Exits with error 22 when the source code is not lexicaly or semantically correct.
 * @param lexemes the array of lexemes. 
 **/
function parse_VT($lexemes)
{
    global $stats, $xml_file;
    $xml_file->add_instruction_opcode($lexemes[0]);

    if (sizeof($lexemes) >= 3)
    {
        if (parse_variable($lexemes[1]))
        {
            exit(LEX_SYN_ERR); // variable cannot be followed by a comment in this case
        }
        if (($ret = parse_type($lexemes[2])) || sizeof($lexemes) > 3)
        {
            // variable is directly followed by a comment or there are more than 2 lexemes, which have to result
            // in comment, if the source code is correct
            $stats->add_comment();
        }
        if (sizeof($lexemes) > 3 && !(substr($lexemes[3], 0, 1) == "#" || $ret))
        {
            exit(LEX_SYN_ERR); // more then 3 lexemes without a comment
        }
    }
    else
    {
        exit(LEX_SYN_ERR); // not enough lexemes for given instruction
    }
}

/**
 * @brief Parses a variable (a string without white spaces). Ignores any comment, if the variable is followed directly by one.
 *        Exits with error 22 when the variable is not lexicaly correct.
 * @param var the variable to be parsed.
 * @return int 1 when the variable is followed by a comment, otherwise 0.
 **/
function parse_variable($var)
{
    global $xml_file;

    $ret_val = strip_comment($var);

    if (preg_match(VARIABLE, $var))
    {
        $xml_file->add_intsruction_argument($var, "var");
    }
    else
    {
        exit(LEX_SYN_ERR); // wrong variable format
    }

    return $ret_val;
}

/**
 * @brief Parses a symbol (a string without white spaces). Ignores any comment, if the symbol is followed directly by one.
 *        Exits with error 22 when the symbol is not lexicaly correct.
 * @param symbol the symbol to be parsed.
 * @return int 1 when the symbol is followed by a comment, otherwise 0.
 **/
function parse_symbol($symbol)
{
    global $xml, $xml_file;

    $ret_val = strip_comment($symbol);

    if (preg_match(VARIABLE, $symbol))
    {
        // the symbol is a variable
        $xml_file->add_intsruction_argument($symbol, "var");
    }
    else if (preg_match(INTGR, $symbol))
    {
        // the symbol is an integer
        if (strlen(substr($symbol, 4)) == 0)
        {
            exit(LEX_SYN_ERR);
        }
        $xml_file->add_intsruction_argument(substr($symbol, 4), "int");
    }
    else if (preg_match(BOOLN, $symbol))
    {
        // the symbol is a boolean
        $xml_file->add_intsruction_argument(substr($symbol, 5), "bool");
    }
    else if (preg_match(NIL, $symbol))
    {
        // the symbol is a nil
        $xml_file->add_intsruction_argument(substr($symbol, 4), "nil");
    }
    else if (substr($symbol, 0, 7) == "string@")
    {
        // the symbol is a string
        parse_string(substr($symbol, 7)); // symbol type is omitted from parsing 
        $xml_file->add_intsruction_argument(substr($symbol, 7), "string");
    }
    else
    {
        exit(LEX_SYN_ERR);
    }

    return $ret_val;
}

/**
 * @brief Parses a label (a string without white spaces). Ignores any comment, if the label is followed directly by one.
 *        Exits with error 22 when the label is not lexicaly correct.
 * @param label the label to be parsed.
 * @return int 1 when the label is followed by a comment, otherwise 0.
 **/
function parse_label($label)
{
    global $xml_file;

    $ret_val = strip_comment($label);

    if (preg_match(LABEL, $label))
    {
        $xml_file->add_intsruction_argument($label, "label");
    }
    else
    {
        exit(LEX_SYN_ERR); // inccorect label format
    }

    return $ret_val;
}

/**
 * @brief Parses a type (a string without white spaces). Ignores any comment, if the type is followed directly by one.
 *        Exits with error 22 when the type is not lexicaly correct.
 * @param type the type to be parsed.
 * @return int 1 when the type is followed by a comment, otherwise 0.
 **/
function parse_type($type)
{
    global $xml_file;

    $ret_val = strip_comment($type);

    if (preg_match(TYPE, $type))
    {
        $xml_file->add_intsruction_argument($type, "type");
    }
    else
    {
        exit(LEX_SYN_ERR); // incorrect type format
    }

    return $ret_val;
}

/**
 * @brief Parses a string literal in a IPPcode21 format. Ignores any comment, if the type is followed directly by one.
 *        Exits with error 22 when the string is not lexicaly correct.
 * @param string the string to be parsed.
 * @return int 1 when the string is followed by a comment, otherwise 0.
 **/
function parse_string($string)
{
    $ret_val = strip_comment($string);

    for ($i = 0; $i < strlen($string); $i++)
    {
        if (ord($string[$i]) <= 32)
        {
            exit(LEX_SYN_ERR); // character with ordinal value less or equal to 32, which cannot be used directly
        }
        else if ($string[$i] == '#')
        {
            exit(LEX_SYN_ERR); // '#' in not allowed character
        }
        else if ($string[$i] == '\\')
        {
            if (!preg_match(STR_ESCAPE, substr($string, $i + 1)))
            {
                exit(LEX_SYN_ERR); // the escape sequence does not have the correct format
            }
            $i = $i + 3;
        }
    }

    return $ret_val;
}

/**
 * @brief Strips a string without white spaces from comment, if there is any.
 * @param str the reference on a string to be parsed.
 * @return int 1 when a comment was stripped, otherwise 0;
 **/
function strip_comment(&$str)
{
    global $stats;
    $pos = strpos($str, "#"); // find the position of a comment start
    if ($pos === false)
    {
        return 0; // there is no comment
    }
    $str = substr($str, 0, $pos); // strip the comment
    return 1;
}

/**
 * @brief Prints the help message to STDOUT.
 **/
function print_help_msg()
{
    echo "Usage: parse.php [option] ...\n";
    echo "Options:\n";
    echo "--help \t\tDisplay help message.\n";
    echo "--stats=<file> \tCollect statistics about parsing in to a file <file>.\n";
    echo "--loc \t\tInclude the number of used instructions.\n";
    echo "--comments \tInclude the number of used commnets.\n";
    echo "--labels \tInclude the number of used labels.\n";
    echo "--jumps \tInclude the number of used jumps.\n";
    echo "--fwjumps \tInclude the number of used forward jumps.\n";
    echo "--backjumps \tInclude the number of used backwards jumps.\n";
    echo "--badjumps \tInclude the number of used incorrect jumps.\n\n";
    echo "Parameter --stats=<file> can be used multiple times, with different file names.\n";
    echo "Parameters other than --help and --stats=<file> can be used only after previous --stats=<file> parameter.\n";
}

// ======================================== end of functions =======================================

?>