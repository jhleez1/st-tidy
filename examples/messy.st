(* A badly formatted program to try st-tidy on:
     python -m st_tidy examples/messy.st --diff --lint *)
program _CYCLIC
if diStart and not diStop then
state:=1;
elsif diStop then
  state:=0;
end_if;

  case state of
  0:
  doMotor:=false;
  1: doMotor:=true;
     Timer(IN:=doMotor,PT:=t#5s);
  end_case;

if Timer.Q then
	Count = Count + 1;   // oops: comparison, not assignment
  Msg:='Done, motor on' // missing semicolon
end_if;
END_PROGRAM
