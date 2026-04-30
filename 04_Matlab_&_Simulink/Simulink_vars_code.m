model = 'MyComplexModel_V13R2023a';
load_system(model);

% Temporary only, to avoid Inf in inactive VAD/graft blocks
L = 1e-6;
R = 1e-6;

vars = Simulink.findVars(model);

n = numel(vars);

Name = strings(n,1);
Source = strings(n,1);
SourceType = strings(n,1);
Users = strings(n,1);

for i = 1:n
    Name(i) = string(vars(i).Name);
    Source(i) = string(vars(i).Source);
    SourceType(i) = string(vars(i).SourceType);

    try
        Users(i) = strjoin(string(vars(i).Users), " | ");
    catch
        Users(i) = "";
    end
end

T = table(Name, Source, SourceType, Users);

writetable(T, 'simulink_used_variables_clean.csv');